"""解析服务：把 SQL 解析成列级血缘边并持久化（先删后插，事务内完成）。"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import log_templates
from app.constants.edge import EDGE_KIND_PRIORITY, EdgeKind
from app.model_helpers import asset_info_from_model
from app.models.data_asset import DataAsset
from app.models.lineage_edge import LineageEdge
from app.models.transformation import Transformation
from app.parsers.context import AssetInfo
from app.parsers.engine import ParseResult, parse_sql
from app.utils.hashing import truncate
from app.utils.logger import log
from app.config.storage import write_json, write_sql

logger = logging.getLogger("datatrace.parse")


def produced_columns_map(db: Session) -> dict[str, set[str]]:
    """asset_id → 其它转换已经产出的目标列（用于判定 SELECT * 能否展开）。"""
    rows = db.execute(select(LineageEdge.target_asset_id, LineageEdge.target_column)).all()
    result: dict[str, set[str]] = {}
    for target_asset_id, target_column in rows:
        result.setdefault(str(target_asset_id), set()).add(target_column)
    return result


def gather_assets(db: Session, asset_ids: list[uuid.UUID], produced: dict[str, set[str]]) -> list[AssetInfo]:
    infos: list[AssetInfo] = []
    for asset_id in asset_ids:
        asset = db.get(DataAsset, uuid.UUID(str(asset_id)))
        if asset is None:
            continue
        infos.append(asset_info_from_model(asset, produced.get(str(asset.id), set())))
    return infos


def _build_report(
    result: ParseResult,
    transformation: Transformation,
    input_assets: list[AssetInfo],
    output_asset: AssetInfo,
) -> dict:
    names = {asset.id: asset.display_name for asset in input_assets}
    names[output_asset.id] = output_asset.display_name
    columns = []
    for target_column, refs in result.columns.items():
        columns.append(
            {
                "target_column": target_column,
                "sources": [
                    {
                        "asset_id": ref.asset_id,
                        "asset_name": names.get(ref.asset_id, ref.asset_id),
                        "column": ref.column,
                        "edge_kind": ref.kind,
                    }
                    for ref in refs
                ],
            }
        )
    return {
        "unresolved": result.unresolved,
        "warnings": result.warnings,
        "star_expanded": result.star_expanded,
        "edge_count": result.edge_count,
        "input_assets": [{"id": a.id, "name": a.display_name} for a in input_assets],
        "output_asset": {"id": output_asset.id, "name": output_asset.display_name},
        "columns": columns,
        "parser": "sqlglot",
        "dialect": transformation.dialect,
    }


def _replace_edges(
    db: Session,
    transformation: Transformation,
    result: ParseResult,
    output_asset_id: uuid.UUID,
    input_ids: set[str],
) -> int:
    deleted = (
        db.query(LineageEdge)
        .filter(LineageEdge.transformation_id == transformation.id)
        .delete(synchronize_session=False)
    )
    dedup: dict[tuple[str, str, str], dict] = {}
    for target_column, refs in result.columns.items():
        for ref in refs:
            if ref.asset_id not in input_ids:
                # 来源必须落在输入资产集合内，避免脏边
                continue
            key = (ref.asset_id, ref.column, target_column)
            candidate = {
                "source_asset_id": uuid.UUID(ref.asset_id),
                "source_column": ref.column,
                "target_asset_id": output_asset_id,
                "target_column": target_column,
                "edge_kind": ref.kind,
                "expression_text": truncate(ref.expression_text or ref.column, 512),
            }
            existing = dedup.get(key)
            if existing is None or _priority(ref.kind) > _priority(existing["edge_kind"]):
                dedup[key] = candidate
    for payload in dedup.values():
        db.add(
            LineageEdge(
                transformation_id=transformation.id,
                source_asset_id=payload["source_asset_id"],
                source_column=payload["source_column"],
                target_asset_id=payload["target_asset_id"],
                target_column=payload["target_column"],
                edge_kind=payload["edge_kind"],
                expression_text=payload["expression_text"],
            )
        )
    db.flush()
    log(
        logger,
        "LINEAGE_EDGES_REBUILT",
        level=logging.INFO,
        transformation=transformation.name,
        inserted=len(dedup),
        deleted=deleted,
    )
    return len(dedup)


def _priority(kind: str) -> int:
    try:
        return EDGE_KIND_PRIORITY[EdgeKind(kind)]
    except ValueError:
        return 0


def parse_transformation(db: Session, transformation: Transformation) -> Transformation:
    """解析一个转换：解析 → 整体替换边集合 → 状态与报告回写。"""
    input_ids = [uuid.UUID(str(x)) for x in (transformation.input_asset_ids_json or [])]
    output_asset = db.get(DataAsset, transformation.output_asset_id)
    if output_asset is None:
        transformation.parse_status = "failed"
        transformation.parse_error = f"输出资产不存在：{transformation.output_asset_id}"
        db.commit()
        return transformation

    produced = produced_columns_map(db)
    input_assets = gather_assets(db, input_ids, produced)
    output_info = asset_info_from_model(output_asset, produced.get(str(output_asset.id), set()))

    log(
        logger,
        "PARSE_START",
        level=logging.INFO,
        transformation=transformation.name,
        dialect=transformation.dialect,
        bytes=len(transformation.sql_text.encode("utf-8")),
    )
    result = parse_sql(
        transformation.sql_text,
        transformation.dialect,
        output_info,
        input_assets,
    )
    result.edge_count = _replace_edges(
        db, transformation, result, output_asset.id, {str(a.id) for a in input_assets}
    )

    transformation.parse_status = result.status
    transformation.parse_error = result.parse_error
    transformation.report_json = _build_report(result, transformation, input_assets, output_info)
    transformation.report_json["status"] = result.status

    if result.status == "failed":
        log(
            logger,
            "PARSE_FAILED_WITH_POS",
            level=logging.WARNING,
            transformation=transformation.name,
            message=(result.parse_error or "")[:200],
            line=result.error_line,
            col=result.error_column,
        )
    elif result.status == "partial":
        for issue in result.unresolved:
            if issue.get("column") == "*":
                log(
                    logger,
                    "PARSE_PARTIAL_STAR",
                    level=logging.WARNING,
                    asset=issue.get("asset_name"),
                    column="*",
                    missing=",".join(issue.get("missing") or []) or "unknown",
                )
        log(
            logger,
            "PARSE_PARTIAL",
            level=logging.WARNING,
            transformation=transformation.name,
            reason="; ".join(u.get("reason", "") for u in result.unresolved),
        )
    else:
        log(
            logger,
            "PARSE_OK",
            level=logging.INFO,
            transformation=transformation.name,
            edges=result.edge_count,
            status=result.status,
        )

    db.commit()
    db.refresh(transformation)

    # 原始 SQL 与解析快照落共享卷（失败不阻塞业务）
    try:
        write_sql(transformation.name, transformation.sql_text)
        write_json(
            "parse-snapshots",
            f"{transformation.name}-v{transformation.version}",
            {
                "transformation": transformation.name,
                "version": transformation.version,
                "dialect": transformation.dialect,
                "status": result.status,
                "parse_error": result.parse_error,
                "report": transformation.report_json,
            },
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("artifact write failed: %s", exc)
    return transformation


def preview(
    db: Session,
    sql_text: str,
    dialect: str,
    output_asset_id: uuid.UUID,
    input_asset_ids: list[uuid.UUID],
) -> ParseResult:
    """轻量试解析：不落库、不改边。"""
    produced = produced_columns_map(db)
    output_asset = db.get(DataAsset, output_asset_id)
    if output_asset is None:
        from app.utils.errors import AppError

        raise AppError("E_NOT_FOUND", "输出资产不存在", entity="data_asset", field="output_asset_id")
    input_assets = gather_assets(db, input_asset_ids, produced)
    output_info = asset_info_from_model(output_asset, produced.get(str(output_asset.id), set()))
    return parse_sql(sql_text, dialect, output_info, input_assets)


def asset_info(db: Session, asset_id: uuid.UUID) -> AssetInfo | None:
    asset = db.get(DataAsset, asset_id)
    if asset is None:
        return None
    return asset_info_from_model(asset, produced_columns_map(db).get(str(asset.id), set()))
