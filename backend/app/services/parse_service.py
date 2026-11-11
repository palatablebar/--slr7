"""解析服务：把 SQL 解析成列级血缘边。

两条入口，语义严格区分：
- ``parse_draft``：解析草稿内容。解析失败只回写草稿状态，**绝不触碰**
  已上线 Transformation 的血缘边、状态与报告；
- ``promote_draft``：草稿解析通过后，在**单个数据库事务**内完成
  「删旧边 → 插新边 → 回写上线 SQL/状态/报告 → 版本号 +1 → 清理草稿」，
  任一步失败整体回滚，保证不会出现只更新了一半关系的中间状态。

未通过校验（parse_status == failed）的草稿永远不会被当成上线版本。
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.edge import EDGE_KIND_PRIORITY, EdgeKind
from app.model_helpers import asset_info_from_model
from app.models.data_asset import DataAsset
from app.models.lineage_edge import LineageEdge
from app.models.transformation import Transformation
from app.models.transformation_draft import TransformationDraft
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
    dialect: str,
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
        "dialect": dialect,
    }


def _priority(kind: str) -> int:
    try:
        return EDGE_KIND_PRIORITY[EdgeKind(kind)]
    except ValueError:
        return 0


def _build_new_edges(
    result: ParseResult,
    transformation: Transformation,
    output_asset_id: uuid.UUID,
    input_ids: set[str],
) -> list[LineageEdge]:
    """根据解析结果构造新边集合（只构造、不写库），便于事务内整体替换。"""
    dedup: dict[tuple[str, str, str], LineageEdge] = {}
    for target_column, refs in result.columns.items():
        for ref in refs:
            if ref.asset_id not in input_ids:
                # 来源必须落在输入资产集合内，避免脏边
                continue
            key = (ref.asset_id, ref.column, target_column)
            candidate = LineageEdge(
                transformation_id=transformation.id,
                source_asset_id=uuid.UUID(ref.asset_id),
                source_column=ref.column,
                target_asset_id=output_asset_id,
                target_column=target_column,
                edge_kind=ref.kind,
                expression_text=truncate(ref.expression_text or ref.column, 512),
            )
            existing = dedup.get(key)
            if existing is None or _priority(ref.kind) > _priority(existing.edge_kind):
                dedup[key] = candidate
    return list(dedup.values())


def _replace_edges(
    db: Session,
    transformation: Transformation,
    result: ParseResult,
    output_asset_id: uuid.UUID,
    input_ids: set[str],
) -> int:
    """删旧边 + 插新边（仅 flush，不 commit），由外层事务决定提交或回滚。"""
    deleted = (
        db.query(LineageEdge)
        .filter(LineageEdge.transformation_id == transformation.id)
        .delete(synchronize_session=False)
    )
    new_edges = _build_new_edges(result, transformation, output_asset_id, input_ids)
    for edge in new_edges:
        db.add(edge)
    db.flush()
    log(
        logger,
        "LINEAGE_EDGES_REBUILT",
        level=logging.INFO,
        transformation=transformation.name,
        inserted=len(new_edges),
        deleted=deleted,
    )
    return len(new_edges)


def _run_parse(
    db: Session,
    *,
    sql_text: str,
    dialect: str,
    input_asset_ids: list[uuid.UUID],
    output_asset_id: uuid.UUID,
) -> tuple[ParseResult | None, list[AssetInfo], AssetInfo | None, str | None]:
    """执行纯解析，返回 (result, input_assets, output_info, fatal_error)。"""
    output_asset = db.get(DataAsset, output_asset_id)
    if output_asset is None:
        return None, [], None, f"输出资产不存在：{output_asset_id}"
    produced = produced_columns_map(db)
    input_assets = gather_assets(db, input_asset_ids, produced)
    output_info = asset_info_from_model(output_asset, produced.get(str(output_asset.id), set()))
    result = parse_sql(sql_text, dialect, output_info, input_assets)
    return result, input_assets, output_info, None


def _log_parse_outcome(result: ParseResult, name: str) -> None:
    if result.status == "failed":
        log(
            logger,
            "PARSE_FAILED_WITH_POS",
            level=logging.WARNING,
            transformation=name,
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
            transformation=name,
            reason="; ".join(u.get("reason", "") for u in result.unresolved),
        )
    else:
        log(
            logger,
            "PARSE_OK",
            level=logging.INFO,
            transformation=name,
            edges=result.edge_count,
            status=result.status,
        )


# --------------------------------------------------------------------------- #
# 草稿解析：失败只动草稿，已上线血缘保持不变
# --------------------------------------------------------------------------- #
def parse_draft(db: Session, draft: TransformationDraft) -> TransformationDraft:
    """解析草稿并把结果写回草稿行；任何情况下都不修改已上线血缘边。"""
    input_ids = [uuid.UUID(str(x)) for x in (draft.input_asset_ids_json or [])]
    log(
        logger,
        "PARSE_START",
        level=logging.INFO,
        transformation=draft.transformation.name if draft.transformation else str(draft.transformation_id),
        dialect=draft.dialect,
        bytes=len(draft.sql_text.encode("utf-8")),
    )
    result, input_assets, output_info, fatal = _run_parse(
        db,
        sql_text=draft.sql_text,
        dialect=draft.dialect,
        input_asset_ids=input_ids,
        output_asset_id=draft.output_asset_id,
    )
    name = draft.transformation.name if draft.transformation else str(draft.transformation_id)
    if fatal is not None:
        # 输出资产缺失等致命问题：仅标记草稿失败，上线版本不动
        draft.parse_status = "failed"
        draft.parse_error = fatal
        draft.error_line = None
        draft.error_column = None
        draft.report_json = {"status": "failed", "parse_error": fatal}
        db.commit()
        db.refresh(draft)
        log(
            logger,
            "DRAFT_PARSE_FAILED",
            level=logging.WARNING,
            transformation=name,
            draft_id=str(draft.id),
            message=fatal[:200],
            line=None,
            col=None,
        )
        return draft

    _log_parse_outcome(result, name)
    draft.parse_status = result.status
    draft.parse_error = result.parse_error
    draft.error_line = result.error_line
    draft.error_column = result.error_column
    report = _build_report(result, draft.dialect, input_assets, output_info)
    report["status"] = result.status
    draft.report_json = report

    if result.status == "failed":
        # 关键保证：解析失败时不执行任何边替换，只提交草稿自身的状态
        db.commit()
        db.refresh(draft)
        log(
            logger,
            "DRAFT_PARSE_FAILED",
            level=logging.WARNING,
            transformation=name,
            draft_id=str(draft.id),
            message=(result.parse_error or "")[:200],
            line=result.error_line,
            col=result.error_column,
        )
        return draft

    db.commit()
    db.refresh(draft)
    log(
        logger,
        "DRAFT_SAVED",
        level=logging.INFO,
        transformation=name,
        draft_id=str(draft.id),
        parse_status=result.status,
    )
    return draft


# --------------------------------------------------------------------------- #
# 上线切换：单事务原子提交，失败整体回滚
# --------------------------------------------------------------------------- #
def promote_draft(db: Session, draft: TransformationDraft) -> Transformation:
    """把通过校验的草稿原子切换为上线版本。

    只有 parse_status 为 parsed / partial 的草稿允许进入；整个切换在一个
    事务内完成，任何异常都会 rollback，已上线血缘与影响分析结果保持原样。
    """
    transformation = draft.transformation
    if transformation is None:
        transformation = db.get(Transformation, draft.transformation_id)
    if transformation is None:
        from app.utils.errors import AppError
        from app.constants.error_codes import E_NOT_FOUND

        raise AppError(E_NOT_FOUND, "转换不存在", entity="transformation", field="id")

    if draft.parse_status == "failed":
        from app.constants.messages import MSG_DRAFT_BUSY
        from app.utils.errors import AppError

        raise AppError(
            "E_PARSE_FAILED",
            MSG_DRAFT_BUSY,
            entity="transformation",
            field="sql_text",
            detail={"parse_error": draft.parse_error},
        )

    # 以草稿内容重新解析一次，确保提交的边与草稿 SQL 严格一致
    # （解析在事务外只读，边的写操作全部放进下面的事务）
    input_ids = [uuid.UUID(str(x)) for x in (draft.input_asset_ids_json or [])]
    result, input_assets, output_info, fatal = _run_parse(
        db,
        sql_text=draft.sql_text,
        dialect=draft.dialect,
        input_asset_ids=input_ids,
        output_asset_id=draft.output_asset_id,
    )
    if fatal is not None or result is None or result.status == "failed":
        reason = fatal or (result.parse_error if result else "解析失败")
        draft.parse_status = "failed"
        draft.parse_error = reason
        if result is not None:
            draft.error_line = result.error_line
            draft.error_column = result.error_column
        db.commit()
        log(
            logger,
            "PROMOTE_ROLLBACK",
            level=logging.WARNING,
            transformation=transformation.name,
            reason=str(reason)[:200],
        )
        from app.constants.messages import MSG_DRAFT_BUSY
        from app.utils.errors import AppError

        raise AppError(
            "E_PARSE_FAILED",
            MSG_DRAFT_BUSY,
            entity="transformation",
            field="sql_text",
            detail={"parse_error": reason},
        )

    try:
        # ---- 单事务原子切换开始（commit 之前任何异常都整体回滚）----
        inserted = _replace_edges(
            db,
            transformation,
            result,
            output_info.id,
            {str(a.id) for a in input_assets},
        )
        result.edge_count = inserted

        transformation.sql_text = draft.sql_text
        transformation.dialect = draft.dialect
        transformation.input_asset_ids_json = [str(x) for x in draft.input_asset_ids_json]
        transformation.output_asset_id = draft.output_asset_id
        transformation.parse_status = result.status
        transformation.parse_error = result.parse_error
        report = _build_report(result, transformation.dialect, input_assets, output_info)
        report["status"] = result.status
        transformation.report_json = report
        transformation.version += 1

        # 草稿已上线，删除草稿行；删边/插边/回写/删草稿同生共死
        db.delete(draft)
        db.commit()
    except Exception:
        db.rollback()
        log(
            logger,
            "PROMOTE_ROLLBACK",
            level=logging.ERROR,
            transformation=transformation.name,
            reason="commit failed",
        )
        raise
    db.refresh(transformation)

    log(
        logger,
        "DRAFT_PROMOTED",
        level=logging.INFO,
        transformation=transformation.name,
        version=transformation.version,
        inserted=inserted,
        deleted=inserted,
    )

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


# --------------------------------------------------------------------------- #
# 兼容入口：对已上线转换直接重新解析（仍走原子事务）
# --------------------------------------------------------------------------- #
def parse_transformation(db: Session, transformation: Transformation) -> Transformation:
    """对已上线转换按当前 SQL 重新解析并原子替换边集合。

    供「重新解析」按钮、seed 与 worker 使用。先删后插与状态回写在同一事务
    内提交；解析失败时回滚边操作，保留原有血缘与状态，仅把失败信息记录到
    转换的 parse_error（不删边）。
    """
    input_ids = [uuid.UUID(str(x)) for x in (transformation.input_asset_ids_json or [])]
    log(
        logger,
        "PARSE_START",
        level=logging.INFO,
        transformation=transformation.name,
        dialect=transformation.dialect,
        bytes=len(transformation.sql_text.encode("utf-8")),
    )
    result, input_assets, output_info, fatal = _run_parse(
        db,
        sql_text=transformation.sql_text,
        dialect=transformation.dialect,
        input_asset_ids=input_ids,
        output_asset_id=transformation.output_asset_id,
    )
    if fatal is not None:
        transformation.parse_status = "failed"
        transformation.parse_error = fatal
        transformation.report_json = {**(transformation.report_json or {}), "status": "failed", "parse_error": fatal}
        db.commit()
        db.refresh(transformation)
        log(
            logger,
            "PARSE_FAILED_WITH_POS",
            level=logging.WARNING,
            transformation=transformation.name,
            message=fatal[:200],
            line=None,
            col=None,
        )
        return transformation

    _log_parse_outcome(result, transformation.name)

    if result.status == "failed":
        # 解析失败：不删边、不替换，保留原有血缘，只回写失败状态与错误
        transformation.parse_status = "failed"
        transformation.parse_error = result.parse_error
        report = _build_report(result, transformation.dialect, input_assets, output_info)
        report["status"] = "failed"
        transformation.report_json = report
        db.commit()
        db.refresh(transformation)
        return transformation

    try:
        inserted = _replace_edges(
            db,
            transformation,
            result,
            output_info.id,
            {str(a.id) for a in input_assets},
        )
        result.edge_count = inserted
        transformation.parse_status = result.status
        transformation.parse_error = result.parse_error
        report = _build_report(result, transformation.dialect, input_assets, output_info)
        report["status"] = result.status
        transformation.report_json = report
        db.commit()
    except Exception:
        db.rollback()
        log(
            logger,
            "PROMOTE_ROLLBACK",
            level=logging.ERROR,
            transformation=transformation.name,
            reason="reparse commit failed",
        )
        raise
    db.refresh(transformation)

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
