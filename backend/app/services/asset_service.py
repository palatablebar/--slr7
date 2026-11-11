"""资产服务：登记、编辑列清单（产生结构变更事件）、删除保护、一跳上下游。"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.constants import log_templates
from app.constants.error_codes import E_ASSET_IN_USE, E_CONFLICT, E_NOT_FOUND
from app.models.data_asset import DataAsset
from app.models.lineage_edge import LineageEdge
from app.models.transformation import Transformation
from app.models.user import User
from app.services import schema_change_service
from app.utils.errors import AppError
from app.utils.formatters import asset_full_name
from app.utils.logger import log

logger = logging.getLogger("datatrace.asset")


def _column_stats(db: Session, asset: DataAsset) -> list[dict]:
    upstream = (
        db.query(LineageEdge.target_column).filter(LineageEdge.target_asset_id == asset.id).all()
    )
    downstream = (
        db.query(LineageEdge.source_column).filter(LineageEdge.source_asset_id == asset.id).all()
    )
    up_count: dict[str, int] = {}
    for (column,) in upstream:
        up_count[column] = up_count.get(column, 0) + 1
    down_count: dict[str, int] = {}
    for (column,) in downstream:
        down_count[column] = down_count.get(column, 0) + 1
    result = []
    for column in asset.columns_json or []:
        name = column.get("name")
        result.append(
            {
                "name": name,
                "data_type": column.get("data_type"),
                "nullable": column.get("nullable", True),
                "ordinal": column.get("ordinal"),
                "description": column.get("description"),
                "upstream_count": up_count.get(name, 0),
                "downstream_count": down_count.get(name, 0),
            }
        )
    return result


def _to_dict(asset: DataAsset, edge_count: int = 0) -> dict:
    return {
        "id": str(asset.id),
        "owner_id": str(asset.owner_id),
        "name": asset.name,
        "asset_type": asset.asset_type,
        "database_name": asset.database_name,
        "schema_name": asset.schema_name,
        "description": asset.description,
        "status": asset.status,
        "updated_at": asset.updated_at.isoformat(),
        "column_count": len(asset.columns_json or []),
        "display_name": asset.display_name,
        "full_name": asset.full_name,
        "edge_count": edge_count,
    }


def list_assets(
    db: Session,
    *,
    q: str | None = None,
    asset_type: str | None = None,
    status: str | None = None,
) -> list[dict]:
    query = db.query(DataAsset)
    if asset_type:
        query = query.filter(DataAsset.asset_type == asset_type)
    if status:
        query = query.filter(DataAsset.status == status)
    assets = query.order_by(DataAsset.schema_name, DataAsset.name).all()
    if q:
        needle = q.lower()
        filtered = []
        for asset in assets:
            column_names = " ".join((c.get("name") or "") for c in asset.columns_json or [])
            haystack = f"{asset.display_name} {asset.full_name} {column_names} {asset.description or ''}".lower()
            if needle in haystack:
                filtered.append(asset)
        assets = filtered
    edge_rows = db.query(LineageEdge.source_asset_id, LineageEdge.target_asset_id).all()
    counts: dict[str, int] = {}
    for source_id, target_id in edge_rows:
        counts[str(source_id)] = counts.get(str(source_id), 0) + 1
        counts[str(target_id)] = counts.get(str(target_id), 0) + 1
    return [_to_dict(asset, counts.get(str(asset.id), 0)) for asset in assets]


def get_asset(db: Session, asset_id: uuid.UUID) -> DataAsset:
    asset = db.get(DataAsset, asset_id)
    if asset is None:
        raise AppError(E_NOT_FOUND, "资产不存在", entity="data_asset", field="id")
    return asset


def get_detail(db: Session, asset_id: uuid.UUID) -> dict:
    asset = get_asset(db, asset_id)
    owner = db.get(User, asset.owner_id)
    edges = (
        db.query(LineageEdge)
        .filter(or_(LineageEdge.source_asset_id == asset.id, LineageEdge.target_asset_id == asset.id))
        .all()
    )
    asset_ids = set()
    for edge in edges:
        asset_ids.add(edge.source_asset_id)
        asset_ids.add(edge.target_asset_id)
    name_map = {}
    if asset_ids:
        for row in db.query(DataAsset).filter(DataAsset.id.in_(asset_ids)).all():
            name_map[row.id] = row

    upstream: dict[str, dict] = {}
    downstream: dict[str, dict] = {}
    for edge in edges:
        if edge.target_asset_id == asset.id and edge.source_asset_id != asset.id:
            source = name_map.get(edge.source_asset_id)
            key = f"{edge.source_asset_id}:{edge.source_column}"
            upstream[key] = {
                "edge_id": edge.id,
                "asset_id": str(edge.source_asset_id),
                "asset_name": source.display_name if source else str(edge.source_asset_id),
                "asset_type": source.asset_type if source else "table",
                "source_column": edge.source_column,
                "target_column": edge.target_column,
                "edge_kind": edge.edge_kind,
                "expression_text": edge.expression_text,
                "transformation_id": str(edge.transformation_id),
            }
        if edge.source_asset_id == asset.id and edge.target_asset_id != asset.id:
            target = name_map.get(edge.target_asset_id)
            key = f"{edge.target_asset_id}:{edge.target_column}"
            downstream[key] = {
                "edge_id": edge.id,
                "asset_id": str(edge.target_asset_id),
                "asset_name": target.display_name if target else str(edge.target_asset_id),
                "asset_type": target.asset_type if target else "table",
                "source_column": edge.source_column,
                "target_column": edge.target_column,
                "edge_kind": edge.edge_kind,
                "expression_text": edge.expression_text,
                "transformation_id": str(edge.transformation_id),
            }

    transformations = db.query(Transformation).order_by(Transformation.name).all()
    producer = [
        {
            "id": str(t.id),
            "name": t.name,
            "parse_status": t.parse_status,
            "version": t.version,
        }
        for t in transformations
        if t.output_asset_id == asset.id
    ]
    consumer = [
        {
            "id": str(t.id),
            "name": t.name,
            "parse_status": t.parse_status,
            "version": t.version,
        }
        for t in transformations
        if str(asset.id) in [str(x) for x in (t.input_asset_ids_json or [])]
    ]

    changes = [
        {
            "id": event.id,
            "change_type": event.change_type,
            "column_name": event.column_name,
            "old_type": event.old_type,
            "new_type": event.new_type,
            "source": event.source,
            "detected_at": event.detected_at.isoformat(),
        }
        for event in schema_change_service.list_for_asset(db, asset.id)
    ]

    from app.services import audit_service
    from app.utils.formatters import asset_type_label, change_type_label, edge_kind_label, parse_status_label

    audits = [
        {
            "id": str(a.id),
            "action": a.action,
            "result": a.result,
            "created_at": a.created_at.isoformat(),
            "actor_id": str(a.actor_id) if a.actor_id else None,
            "payload_json": a.payload_json,
        }
        for a in audit_service.recent(db, limit=10, entity_type="data_asset", entity_id=str(asset.id))
    ]

    detail = _to_dict(asset, len(edges))
    detail.update(
        {
            "columns": _column_stats(db, asset),
            "owner_display_name": owner.display_name if owner else None,
            "upstream_assets": list(upstream.values()),
            "downstream_assets": list(downstream.values()),
            "producer_transformations": producer,
            "consumer_transformations": consumer,
            "schema_changes": changes,
            "recent_audits": audits,
            "schema_change_labels": [change_type_label(c["change_type"]) for c in changes],
            "asset_type_label": asset_type_label(asset.asset_type),
            "parse_status_labels": {
                t["name"]: parse_status_label(t["parse_status"]) for t in producer + consumer
            },
            "edge_kind_labels": {
                key: edge_kind_label(value["edge_kind"])
                for key, value in {**upstream, **downstream}.items()
            },
        }
    )
    return detail


def create_asset(db: Session, user: User, payload: dict) -> DataAsset:
    duplicate = (
        db.query(DataAsset)
        .filter(
            DataAsset.database_name == payload["database_name"],
            DataAsset.schema_name == payload["schema_name"],
            DataAsset.name == payload["name"],
        )
        .first()
    )
    if duplicate is not None:
        raise AppError(
            E_CONFLICT,
            f"资产 {payload['database_name']}.{payload['schema_name']}.{payload['name']} 已登记",
            entity="data_asset",
            field="name",
        )
    columns = _normalize_columns(payload.get("columns_json") or [])
    asset = DataAsset(
        owner_id=user.id,
        name=payload["name"],
        asset_type=payload.get("asset_type", "table"),
        database_name=payload.get("database_name", "lanzo_dw"),
        schema_name=payload["schema_name"],
        columns_json=columns,
        description=payload.get("description"),
        status=payload.get("status", "active"),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    log(logger, "ASSET_CREATED", level=logging.INFO, asset=asset.full_name, type=asset.asset_type)
    return asset


def update_asset(db: Session, user: User, asset_id: uuid.UUID, payload: dict) -> tuple[DataAsset, list[dict]]:
    asset = get_asset(db, asset_id)
    old_columns = list(asset.columns_json or [])
    changes: list[dict] = []
    if payload.get("columns_json") is not None:
        new_columns = _normalize_columns(payload["columns_json"])
        changes = schema_change_service.diff_columns(old_columns, new_columns)
        asset.columns_json = new_columns
    for field in ("name", "asset_type", "description", "status"):
        if payload.get(field) is not None:
            setattr(asset, field, payload[field])
    for change in changes:
        schema_change_service.record(
            db,
            asset,
            change["change_type"],
            change["column_name"],
            change["old_type"],
            change["new_type"],
            source="manual",
        )
    db.commit()
    db.refresh(asset)
    log(
        logger,
        "ASSET_UPDATED",
        level=logging.INFO,
        asset=asset.full_name,
        columns=len(asset.columns_json or []),
    )
    return asset, changes


def delete_asset(db: Session, asset: DataAsset) -> None:
    edge = (
        db.query(LineageEdge)
        .filter(or_(LineageEdge.source_asset_id == asset.id, LineageEdge.target_asset_id == asset.id))
        .first()
    )
    transformation = (
        db.query(Transformation)
        .filter(
            or_(
                Transformation.output_asset_id == asset.id,
                Transformation.input_asset_ids_json.contains([str(asset.id)]),
            )
        )
        .first()
    )
    if edge is not None or transformation is not None:
        raise AppError(
            E_ASSET_IN_USE,
            "资产仍被转换或血缘边引用，请先解除引用",
            entity="data_asset",
            field="id",
        )
    db.delete(asset)
    db.commit()
    log(logger, "ASSET_DELETED", level=logging.INFO, asset=asset.full_name)


def _normalize_columns(columns: list) -> list[dict]:
    normalized = []
    for index, column in enumerate(columns):
        if hasattr(column, "model_dump"):
            column = column.model_dump()
        name = (column.get("name") or "").strip()
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "data_type": column.get("data_type"),
                "nullable": bool(column.get("nullable", True)),
                "ordinal": column.get("ordinal") if column.get("ordinal") is not None else index + 1,
                "description": column.get("description"),
            }
        )
    return normalized
