"""JWT 签发与校验（access 12h / refresh 7d）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config.settings import settings


def create_access_token(subject: str, role: str) -> str:
    return _create(subject, role, "access", timedelta(hours=settings.access_token_hours))


def create_refresh_token(subject: str, role: str) -> str:
    return _create(subject, role, "refresh", timedelta(days=settings.refresh_token_days))


def _create(subject: str, role: str, token_type: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
