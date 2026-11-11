"""SQLAlchemy 引擎与会话。"""
from __future__ import annotations

import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings

logger = logging.getLogger("datatrace.db")

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(max_attempts: int = 30) -> None:
    """建表（生产可换成 alembic upgrade head）。"""
    from app import models  # noqa: F401  触发模型注册

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("database schema ready (attempt %s)", attempt)
            return
        except Exception as exc:  # pragma: no cover - 仅启动期兜底
            last_error = exc
            logger.warning("database not ready attempt=%s error=%s", attempt, exc)
            time.sleep(1.5)
    raise RuntimeError(f"database init failed: {last_error}")
