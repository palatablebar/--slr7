"""影响分析任务：可达性 + 定级 + 报告落库。"""
from __future__ import annotations

import logging
import time
import uuid

from worker.celery_app import celery_app

logger = logging.getLogger("datatrace.worker.impact")


@celery_app.task(bind=True, name="run_impact_analysis", max_retries=2, retry_backoff=3)
def run_impact_analysis_task(
    self,
    *,
    user_id: str,
    target_asset_id: str,
    target_column: str | None,
    change_type: str,
    force: bool = False,
) -> dict:
    from app.config.database import SessionLocal
    from app.models.user import User
    from app.services import impact_service

    started = time.time()
    db = SessionLocal()
    try:
        user = db.get(User, uuid.UUID(str(user_id)))
        if user is None:
            return {"ok": False, "error": "user not found"}
        analysis, cached = impact_service.analyze(
            db,
            user,
            target_asset_id=uuid.UUID(str(target_asset_id)),
            target_column=target_column,
            change_type=change_type,
            force=force,
        )
        return {
            "ok": True,
            "analysis_id": str(analysis.id),
            "severity": analysis.severity,
            "affected_count": analysis.affected_count,
            "cached": cached,
            "elapsed_ms": round((time.time() - started) * 1000),
        }
    except Exception as exc:  # pragma: no cover
        logger.exception("impact task failed")
        raise self.retry(exc=exc)
    finally:
        db.close()
