"""配额路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.constants.limits import DEFAULT_PARSE_QUOTA
from app.middlewares.auth import get_current_user
from app.models.user import User
from app.services import quota_service

router = APIRouter(prefix="/api/quota", tags=["quota"])


@router.get("/me")
def my_quota(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    quota = quota_service.get_or_create(db, user)
    return {
        "user_id": str(quota.user_id),
        "max_sql_bytes": quota.max_sql_bytes,
        "max_concurrent_parses": quota.max_concurrent_parses,
        "parses_used": quota.parses_used,
        "window_start": quota.window_start.isoformat(),
        "remaining": max(0, DEFAULT_PARSE_QUOTA - quota.parses_used),
        "max_parses": DEFAULT_PARSE_QUOTA,
    }
