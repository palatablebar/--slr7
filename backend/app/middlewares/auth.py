"""JWT 认证：解析 Authorization: Bearer，注入 request.state.user。"""
from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.constants.error_codes import E_UNAUTHORIZED
from app.models.user import User
from app.utils.errors import AppError
from app.utils.jwt import decode_token


def _extract_token(request: Request) -> str | None:
    header = request.headers.get("Authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    cached = getattr(request.state, "user", None)
    if isinstance(cached, User):
        return cached
    token = _extract_token(request)
    if not token:
        raise AppError(E_UNAUTHORIZED, "缺少 Authorization: Bearer 令牌")
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise AppError(E_UNAUTHORIZED, "令牌无效或已过期")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise AppError(E_UNAUTHORIZED, "令牌主体无效")
    user = db.get(User, user_id)
    if user is None:
        raise AppError(E_UNAUTHORIZED, "用户不存在")
    request.state.user = user
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    try:
        return get_current_user(request, db)
    except AppError:
        return None
