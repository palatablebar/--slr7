"""认证控制器：装配 token 与用户响应。"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.constants import log_templates
from app.constants.error_codes import E_UNAUTHORIZED
from app.models.user import User
from app.utils.errors import AppError
from app.utils.jwt import create_access_token, create_refresh_token, decode_token
from app.utils.logger import log
from app.utils.password import verify_password

logger = logging.getLogger("datatrace.auth")


def user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
    }


def login(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None or not verify_password(password, user.password_hash):
        log(logger, "AUTH_LOGIN_FAIL", level=logging.WARNING, email=email)
        raise AppError(E_UNAUTHORIZED, "邮箱或密码不正确", entity="auth", field="password")
    log(logger, "AUTH_LOGIN_OK", level=logging.INFO, user=email, role=user.role)
    return {
        "access_token": create_access_token(str(user.id), user.role),
        "refresh_token": create_refresh_token(str(user.id), user.role),
        "token_type": "bearer",
        "user": user_payload(user),
    }


def refresh(db: Session, refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise AppError(E_UNAUTHORIZED, "refresh token 无效或已过期")
    import uuid

    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise AppError(E_UNAUTHORIZED, "用户不存在")
    return {
        "access_token": create_access_token(str(user.id), user.role),
        "refresh_token": create_refresh_token(str(user.id), user.role),
        "token_type": "bearer",
        "user": user_payload(user),
    }
