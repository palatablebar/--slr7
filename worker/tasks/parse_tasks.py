"""解析任务：解析 SQL + 边集合整体替换 + 状态回写。"""
from __future__ import annotations

import logging
import time
import uuid

from worker.celery_app import celery_app

logger = logging.getLogger("datatrace.worker.parse")


@celery_app.task(bind=True, name="parse_transformation", max_retries=2, retry_backoff=3)
def parse_transformation_task(self, transformation_id: str) -> dict:
    from app.config.database import SessionLocal
    from app.models.transformation import Transformation
    from app.services import parse_service

    started = time.time()
    db = SessionLocal()
    try:
        transformation = db.get(Transformation, uuid.UUID(str(transformation_id)))
        if transformation is None:
            return {"ok": False, "error": "transformation not found"}
        transformation = parse_service.parse_transformation(db, transformation)
        return {
            "ok": transformation.parse_status != "failed",
            "transformation_id": str(transformation.id),
            "parse_status": transformation.parse_status,
            "edge_count": (transformation.report_json or {}).get("edge_count", 0),
            "elapsed_ms": round((time.time() - started) * 1000),
        }
    except Exception as exc:  # pragma: no cover - broker 侧重试
        logger.exception("parse task failed")
        raise self.retry(exc=exc)
    finally:
        db.close()
