"""资产控制器：响应包装（附中文标签）。"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import asset_service
from app.utils.formatters import asset_type_label


def list_payload(db: Session, **filters) -> dict:
    items = asset_service.list_assets(db, **filters)
    for item in items:
        item["asset_type_label"] = asset_type_label(item["asset_type"])
    groups: dict[str, list[dict]] = {}
    for item in items:
        key = f"{item['database_name']}.{item['schema_name']}"
        groups.setdefault(key, []).append(item)
    return {"items": items, "total": len(items), "groups": groups}


def detail_payload(db: Session, asset_id: uuid.UUID) -> dict:
    return asset_service.get_detail(db, asset_id)


def create_payload(db: Session, user: User, payload: dict) -> dict:
    asset = asset_service.create_asset(db, user, payload)
    return asset_service.list_assets(db)[0] if False else {
        "id": str(asset.id),
        "name": asset.display_name,
        "asset_type": asset.asset_type,
        "column_count": len(asset.columns_json or []),
        "message": "资产已登记",
    }


def update_payload(db: Session, user: User, asset_id: uuid.UUID, payload: dict) -> dict:
    asset, changes = asset_service.update_asset(db, user, asset_id, payload)
    return {
        "id": str(asset.id),
        "name": asset.display_name,
        "column_count": len(asset.columns_json or []),
        "schema_changes": changes,
        "message": f"资产已更新，生成 {len(changes)} 条结构变更事件",
    }
