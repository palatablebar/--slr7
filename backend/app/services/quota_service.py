"""解析配额与并发限流。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.constants import log_templates
from app.constants.error_codes import E_PARSE_QUOTA
from app.constants.limits import DEFAULT_MAX_CONCURRENT_PARSES, DEFAULT_MAX_SQL_BYTES, DEFAULT_PARSE_QUOTA
from app.models.quota import Quota
from app.models.user import User
from app.utils.errors import AppError
from app.utils.logger import log

logger = logging.getLogger("datatrace.quota")

# 进程内并发计数（单实例近似；多副本时可换成 Redis 计数）
_inflight: dict[str, int] = {}


def get_or_create(db: Session, user: User) -> Quota:
    quota = db.get(Quota, user.id)
    if quota is None:
        quota = Quota(
            user_id=user.id,
            max_sql_bytes=DEFAULT_MAX_SQL_BYTES,
            max_concurrent_parses=DEFAULT_MAX_CONCURRENT_PARSES,
            parses_used=0,
            window_start=datetime.now(timezone.utc),
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)
    return quota


def remaining(quota: Quota) -> int:
    return max(0, DEFAULT_PARSE_QUOTA - quota.parses_used)


def check(db: Session, user: User, sql_text: str) -> Quota:
    quota = get_or_create(db, user)
    sql_bytes = len(sql_text.encode("utf-8"))
    if sql_bytes > quota.max_sql_bytes:
        log(
            logger,
            "PARSE_GUARD_REJECT",
            level=logging.WARNING,
            user=str(user.id),
            reason="sql_too_large",
            bytes=sql_bytes,
        )
        raise AppError(
            "E_VALIDATION",
            f"SQL 长度 {sql_bytes} 字节超过配额上限 {quota.max_sql_bytes} 字节",
            entity="quota",
            field="sql_text",
        )
    inflight = _inflight.get(str(user.id), 0)
    if inflight >= quota.max_concurrent_parses:
        raise AppError(
            E_PARSE_QUOTA,
            f"并发解析数已达上限 {quota.max_concurrent_parses}，请稍后重试",
            entity="quota",
            field="max_concurrent_parses",
        )
    if remaining(quota) <= 0:
        log(
            logger,
            "PARSE_QUOTA_REJECT",
            level=logging.WARNING,
            user=str(user.id),
            used=quota.parses_used,
            max=DEFAULT_PARSE_QUOTA,
        )
        raise AppError(E_PARSE_QUOTA, entity="quota", field="parses_used")
    return quota


def consume(db: Session, user: User) -> Quota:
    quota = get_or_create(db, user)
    quota.parses_used += 1
    db.commit()
    db.refresh(quota)
    return quota


def enter(user_id: str) -> None:
    _inflight[user_id] = _inflight.get(user_id, 0) + 1


def leave(user_id: str) -> None:
    _inflight[user_id] = max(0, _inflight.get(user_id, 1) - 1)
