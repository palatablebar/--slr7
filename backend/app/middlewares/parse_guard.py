"""解析合规检查：SQL 字节数 / 并发数 / 8 秒超时配额。"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.constants import log_templates
from app.constants.limits import PARSE_TIMEOUT_SECONDS
from app.models.user import User
from app.services import quota_service
from app.utils.logger import log
from app.utils.errors import AppError

logger = logging.getLogger("datatrace.parse_guard")


class ParseGuard:
    """上下文管理器：进入时占用并发额度，退出时释放。"""

    def __init__(self, db: Session, user: User, sql_text: str):
        self.db = db
        self.user = user
        self.sql_text = sql_text
        self.quota = None

    def __enter__(self):
        self.quota = quota_service.check(self.db, self.user, self.sql_text)
        quota_service.enter(str(self.user.id))
        return self

    def __exit__(self, exc_type, exc, tb):
        quota_service.leave(str(self.user.id))
        return False


def ensure_not_timeout(elapsed_seconds: float) -> None:
    if elapsed_seconds > PARSE_TIMEOUT_SECONDS:
        raise AppError(
            "E_PARSE_TIMEOUT",
            f"解析耗时 {elapsed_seconds:.1f}s 超过 {PARSE_TIMEOUT_SECONDS}s 上限，已保留已解析部分",
            entity="parse",
            field="elapsed",
            detail={"elapsed_seconds": round(elapsed_seconds, 2)},
        )
