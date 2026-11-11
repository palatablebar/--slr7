"""审计路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middlewares.auth import get_current_user
from app.models.user import User
from app.services import audit_service
from app.utils.formatters import asset_type_label

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/recent")
def recent(
    limit: int = Query(default=20, ge=1, le=100),
    entity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    rows = audit_service.recent(db, limit=limit, entity_type=entity_type)
    items = [
        {
            "id": str(row.id),
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "payload_json": row.payload_json,
            "ip": row.ip,
            "result": row.result,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {"items": items, "total": len(items)}
