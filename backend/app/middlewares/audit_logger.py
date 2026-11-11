"""审计中间件：统一记录写请求（SQL 原文不落审计表，只存 sha256 与长度）。"""
from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config.database import SessionLocal
from app.constants import log_templates
from app.services import audit_service
from app.utils.logger import log

logger = logging.getLogger("datatrace.audit")

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
WHITELIST_PREFIXES = ("/api/health", "/api/auth/")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method not in WRITE_METHODS:
            return response
        path = request.url.path
        if any(path.startswith(prefix) for prefix in WHITELIST_PREFIXES):
            return response
        user = getattr(request.state, "user", None)
        actor_id = getattr(user, "id", None)
        action = getattr(request.state, "audit_action", None) or f"{request.method} {path}"
        entity_type = getattr(request.state, "audit_entity_type", None) or path.strip("/").split("/")[1:2]
        if isinstance(entity_type, list):
            entity_type = entity_type[0] if entity_type else "unknown"
        entity_id = getattr(request.state, "audit_entity_id", None)
        payload = getattr(request.state, "audit_payload", None) or {}
        result = "ok" if response.status_code < 400 else "error"
        if payload.get("sql_text"):
            from app.utils.hashing import sha256_text

            sql_text = payload.pop("sql_text")
            payload["sql_sha256"] = sha256_text(sql_text)
            payload["sql_bytes"] = len(sql_text.encode("utf-8"))
        try:
            db = SessionLocal()
            try:
                audit_service.record(
                    db,
                    actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    payload=payload,
                    ip=request.client.host if request.client else None,
                    result=result,
                )
            finally:
                db.close()
        except Exception as exc:  # pragma: no cover
            logger.warning("audit write failed: %s", exc)
        return response


def mark(request: Request, *, action: str, entity_type: str, entity_id=None, payload: dict | None = None) -> None:
    request.state.audit_action = action
    request.state.audit_entity_type = entity_type
    request.state.audit_entity_id = str(entity_id) if entity_id else None
    request.state.audit_payload = payload or {}
