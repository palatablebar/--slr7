"""转换服务：新建/改 SQL（版本号 +1）/重新解析/列映射查询。"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.constants import log_templates
from app.constants.error_codes import E_CONFLICT, E_NOT_FOUND
from app.models.data_asset import DataAsset
from app.models.lineage_edge import LineageEdge
from app.models.transformation import Transformation
from app.models.user import User
from app.services import parse_service
from app.utils.errors import AppError
from app.utils.logger import log

logger = logging.getLogger("datatrace.transformation")


def _edge_count(db: Session, transformation_id: uuid.UUID) -> int:
    return db.query(LineageEdge).filter(LineageEdge.transformation_id == transformation_id).count()


def _to_dict(db: Session, transformation: Transformation) -> dict:
    output_asset = db.get(DataAsset, transformation.output_asset_id)
    owner = db.get(User, transformation.owner_id)
    return {
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
    }


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


def update_transformation(
    db: Session, user: User, transformation_id: uuid.UUID, payload: dict
) -> Transformation:
    transformation = get_transformation(db, transformation_id)
    changed = False
    if payload.get("sql_text") is not None and payload["sql_text"] != transformation.sql_text:
        transformation.sql_text = payload["sql_text"]
        changed = True
    if payload.get("dialect") is not None and payload["dialect"] != transformation.dialect:
        transformation.dialect = payload["dialect"]
        changed = True
    if payload.get("name") is not None and payload["name"] != transformation.name:
        transformation.name = payload["name"]
        changed = True
    if payload.get("input_asset_ids_json") is not None:
        transformation.input_asset_ids_json = [str(x) for x in payload["input_asset_ids_json"]]
        changed = True
    if payload.get("output_asset_id") is not None:
        transformation.output_asset_id = payload["output_asset_id"]
        changed = True
    if changed:
        transformation.version += 1
        db.commit()
        db.refresh(transformation)
        log(
            logger,
            "AUDIT_SQL_CHANGED",
            level=logging.INFO,
            actor=str(user.id),
            transformation=transformation.name,
            version=transformation.version,
            sha256="",
        )
        return parse_service.parse_transformation(db, transformation)
    return transformation
