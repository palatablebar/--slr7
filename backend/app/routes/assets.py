"""资产路由（登记/编辑列清单/删除保护/一跳上下游）。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import asset_controller
from app.middlewares import audit_logger
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_capability
from app.models.user import User
from app.schemas.data_asset import AssetCreate, AssetUpdate
from app.services import asset_service

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
def list_assets(
    q: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return asset_controller.list_payload(db, q=q, asset_type=asset_type, status=status)


@router.post("")
def create_asset(
    payload: AssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("asset:write")),
) -> dict:
    result = asset_controller.create_payload(db, user, payload.model_dump())
    audit_logger.mark(
        request,
        action="ASSET_CREATED",
        entity_type="data_asset",
        entity_id=result["id"],
        payload={"asset": result["name"]},
    )
    return result


@router.get("/{asset_id}")
def get_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return asset_controller.detail_payload(db, asset_id)


@router.patch("/{asset_id}")
def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("asset:write")),
) -> dict:
    result = asset_controller.update_payload(db, user, asset_id, payload.model_dump(exclude_unset=True))
    audit_logger.mark(
        request,
        action="ASSET_UPDATED",
        entity_type="data_asset",
        entity_id=asset_id,
        payload={"schema_changes": result.get("schema_changes", [])},
    )
    return result


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("asset:write")),
) -> dict:
    from app.services import permission_service
    from app.constants.roles import Role

    if user.role != Role.admin.value:
        permission_service.ensure(user.role, "asset:delete")
    asset = asset_service.get_asset(db, asset_id)
    name = asset.full_name
    asset_service.delete_asset(db, asset)
    audit_logger.mark(
        request, action="ASSET_DELETED", entity_type="data_asset", entity_id=asset_id, payload={"asset": name}
    )
    return {"message": "资产已删除", "id": str(asset_id)}
