"""转换服务：草稿保存 / 上线发布 / 重新解析 / 列映射查询。

编辑流程（保存即"存草稿 + 校验"）：
1. 修改内容写入 ``TransformationDraft``，已上线 Transformation 不动；
2. 对草稿做解析：
   - 解析失败：错误信息留在草稿，已上线血缘边、状态、影响分析完全不变；
   - 解析通过：在单事务内把草稿原子切换为上线版本（边整体替换 + 版本 +1）。
未通过校验的草稿永远不会被发布，也不会被血缘图 / 影响分析读到。
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.constants.error_codes import E_CONFLICT, E_NOT_FOUND
from app.models.data_asset import DataAsset
from app.models.lineage_edge import LineageEdge
from app.models.transformation import Transformation
from app.models.transformation_draft import TransformationDraft
from app.models.user import User
from app.services import parse_service
from app.utils.errors import AppError
from app.utils.logger import log

logger = logging.getLogger("datatrace.transformation")


def _edge_count(db: Session, transformation_id: uuid.UUID) -> int:
    return db.query(LineageEdge).filter(LineageEdge.transformation_id == transformation_id).count()


def _draft_to_dict(draft: TransformationDraft) -> dict:
    return {
        "id": str(draft.id),
        "sql_text": draft.sql_text,
        "dialect": draft.dialect,
        "input_asset_ids_json": [str(x) for x in (draft.input_asset_ids_json or [])],
        "output_asset_id": str(draft.output_asset_id),
        "parse_status": draft.parse_status,
        "parse_error": draft.parse_error,
        "error_line": draft.error_line,
        "error_column": draft.error_column,
        "report_json": draft.report_json or {},
        "updated_at": draft.updated_at.isoformat(),
    }


def _to_dict(db: Session, transformation: Transformation) -> dict:
    output_asset = db.get(DataAsset, transformation.output_asset_id)
    owner = db.get(User, transformation.owner_id)
    data = {
        "id": str(transformation.id),
        "owner_id": str(transformation.owner_id),
        "name": transformation.name,
        "dialect": transformation.dialect,
        "sql_text": transformation.sql_text,
        "input_asset_ids_json": [str(x) for x in (transformation.input_asset_ids_json or [])],
        "output_asset_id": str(transformation.output_asset_id),
        "parse_status": transformation.parse_status,
        "parse_error": transformation.parse_error,
        "report_json": transformation.report_json or {},
        "version": transformation.version,
        "updated_at": transformation.updated_at.isoformat(),
        "output_asset_name": output_asset.display_name if output_asset else None,
        "owner_display_name": owner.display_name if owner else None,
        "edge_count": _edge_count(db, transformation.id),
        "draft": _draft_to_dict(transformation.draft) if transformation.draft else None,
        "has_draft": transformation.draft is not None,
    }
    return data


def list_transformations(db: Session) -> list[dict]:
    rows = db.query(Transformation).order_by(Transformation.name).all()
    return [_to_dict(db, row) for row in rows]


def get_transformation(db: Session, transformation_id: uuid.UUID) -> Transformation:
    transformation = db.get(Transformation, transformation_id)
    if transformation is None:
        raise AppError(E_NOT_FOUND, "转换不存在", entity="transformation", field="id")
    return transformation


def get_detail(db: Session, transformation_id: uuid.UUID) -> dict:
    transformation = get_transformation(db, transformation_id)
    detail = _to_dict(db, transformation)
    input_ids = [uuid.UUID(str(x)) for x in (transformation.input_asset_ids_json or [])]
    assets = db.query(DataAsset).filter(DataAsset.id.in_(input_ids)).all() if input_ids else []
    detail["input_assets"] = [
        {"id": str(a.id), "name": a.display_name, "asset_type": a.asset_type} for a in assets
    ]
    edges = (
        db.query(LineageEdge)
        .filter(LineageEdge.transformation_id == transformation.id)
        .order_by(LineageEdge.target_column, LineageEdge.source_column)
        .all()
    )
    detail["edges"] = [
        {
            "id": edge.id,
            "source_asset_id": str(edge.source_asset_id),
            "source_column": edge.source_column,
            "target_asset_id": str(edge.target_asset_id),
            "target_column": edge.target_column,
            "edge_kind": edge.edge_kind,
            "expression_text": edge.expression_text,
        }
        for edge in edges
    ]
    return detail


def create_transformation(db: Session, user: User, payload: dict) -> Transformation:
    existing = db.query(Transformation).filter(Transformation.name == payload["name"]).first()
    if existing is not None:
        raise AppError(E_CONFLICT, f"转换 {payload['name']} 已存在", entity="transformation", field="name")
    transformation = Transformation(
        owner_id=user.id,
        name=payload["name"],
        dialect=payload.get("dialect") or "postgres",
        sql_text=payload["sql_text"],
        input_asset_ids_json=[str(x) for x in payload["input_asset_ids_json"]],
        output_asset_id=payload["output_asset_id"],
        parse_status="pending",
        version=1,
        report_json={},
    )
    db.add(transformation)
    db.commit()
    db.refresh(transformation)
    return parse_service.parse_transformation(db, transformation)


def _get_or_create_draft(db: Session, transformation: Transformation, user: User) -> TransformationDraft:
    draft = transformation.draft
    if draft is None:
        draft = TransformationDraft(
            transformation_id=transformation.id,
            updated_by_id=user.id,
            sql_text=transformation.sql_text,
            dialect=transformation.dialect,
            input_asset_ids_json=[str(x) for x in (transformation.input_asset_ids_json or [])],
            output_asset_id=transformation.output_asset_id,
            parse_status="pending",
            report_json={},
        )
        db.add(draft)
        db.flush()
    return draft


def save_draft(
    db: Session, user: User, transformation_id: uuid.UUID, payload: dict
) -> tuple[Transformation, TransformationDraft | None]:
    """保存编辑为草稿并立即校验。

    返回 (transformation, promoted_draft)：
    - 草稿解析失败：promoted_draft 为 None，转换的上线内容与血缘不变，
      错误信息保存在 transformation.draft 中；
    - 草稿解析通过：草稿被原子发布，transformation 已是新版本。
    """
    transformation = get_transformation(db, transformation_id)

    # name 属于元数据，不参与 SQL 草稿校验，直接改主表（不改变血缘）
    name_only_change = False
    if payload.get("name") is not None and payload["name"] != transformation.name:
        clash = (
            db.query(Transformation)
            .filter(Transformation.name == payload["name"], Transformation.id != transformation.id)
            .first()
        )
        if clash is not None:
            raise AppError(
                E_CONFLICT, f"转换 {payload['name']} 已存在", entity="transformation", field="name"
            )
        transformation.name = payload["name"]
        name_only_change = True

    # 只有草稿相关字段（SQL/方言/输入输出资产）才进入草稿校验流程
    draft_fields = ("sql_text", "dialect", "input_asset_ids_json", "output_asset_id")
    has_draft_change = any(payload.get(field) is not None for field in draft_fields)
    if not has_draft_change and transformation.draft is None:
        # 纯改名等元数据更新：不建草稿、不解析、不动版本号与血缘
        if name_only_change:
            db.commit()
            db.refresh(transformation)
        return transformation, None

    draft = _get_or_create_draft(db, transformation, user)
    draft.updated_by_id = user.id
    if payload.get("sql_text") is not None:
        draft.sql_text = payload["sql_text"]
    if payload.get("dialect") is not None:
        draft.dialect = payload["dialect"]
    if payload.get("input_asset_ids_json") is not None:
        draft.input_asset_ids_json = [str(x) for x in payload["input_asset_ids_json"]]
    if payload.get("output_asset_id") is not None:
        draft.output_asset_id = payload["output_asset_id"]
    # 每次保存都是一次新的校验，先重置为 pending，避免沿用上次结论
    draft.parse_status = "pending"
    draft.parse_error = None
    draft.error_line = None
    draft.error_column = None
    draft.report_json = {}
    db.commit()
    db.refresh(draft)

    # 1) 只解析草稿：失败写草稿，上线血缘不受影响
    parse_service.parse_draft(db, draft)
    db.refresh(transformation)

    # 2) 解析通过 → 单事务原子切换为上线版本
    if draft.parse_status in ("parsed", "partial"):
        transformation = parse_service.promote_draft(db, draft)
        return transformation, None

    log(
        logger,
        "AUDIT_SQL_CHANGED",
        level=logging.INFO,
        actor=str(user.id),
        transformation=transformation.name,
        version=transformation.version,
        sha256="",
        note="draft saved with parse failure; published lineage untouched",
    )
    db.refresh(transformation)
    return transformation, transformation.draft


def discard_draft(db: Session, user: User, transformation_id: uuid.UUID) -> Transformation:
    """丢弃未上线草稿，恢复到当前上线版本。"""
    transformation = get_transformation(db, transformation_id)
    draft = transformation.draft
    if draft is not None:
        log(
            logger,
            "DRAFT_DISCARDED",
            level=logging.INFO,
            transformation=transformation.name,
            draft_id=str(draft.id),
        )
        db.delete(draft)
        db.commit()
        db.refresh(transformation)
    return transformation


def update_transformation(
    db: Session, user: User, transformation_id: uuid.UUID, payload: dict
) -> Transformation:
    """兼容旧调用：保存草稿，解析通过则返回上线后的转换，否则返回原转换（草稿挂在其上）。"""
    transformation, _draft = save_draft(db, user, transformation_id, payload)
    return transformation
