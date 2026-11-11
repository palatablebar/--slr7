"""审计日志写入与查询。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    actor_id,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    payload: dict | None = None,
    ip: str | None = None,
    result: str = "ok",
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        payload_json=payload or {},
        ip=ip,
        result=result,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def recent(db: Session, limit: int = 20, entity_type: str | None = None, entity_id: str | None = None):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == str(entity_id))
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
