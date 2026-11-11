"""转换路由：新建/改 SQL/重新解析/试解析/异步任务。"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import transformation_controller
from app.middlewares import audit_logger
from app.middlewares.auth import get_current_user
from app.middlewares.parse_guard import ParseGuard, ensure_not_timeout
from app.middlewares.rbac import require_capability
from app.models.user import User
from app.schemas.transformation import ParseRequest, TransformationCreate, TransformationUpdate
from app.services import parse_service, quota_service, transformation_service
from app.utils.logger import log

logger = logging.getLogger("datatrace.routes.transformation")

router = APIRouter(prefix="/api/transformations", tags=["transformations"])
tasks_router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_transformations(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return transformation_controller.list_payload(db)


@router.post("")
def create_transformation(
    payload: TransformationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("transformation:write")),
) -> dict:
    started = time.time()
    with ParseGuard(db, user, payload.sql_text):
        transformation = transformation_service.create_transformation(db, user, payload.model_dump())
    ensure_not_timeout(time.time() - started)
    quota_service.consume(db, user)
    audit_logger.mark(
        request,
        action="AUDIT_SQL_CHANGED",
        entity_type="transformation",
        entity_id=transformation.id,
        payload={"sql_text": transformation.sql_text, "version": transformation.version},
    )
    return transformation_controller.detail_payload(db, transformation.id)


@router.get("/{transformation_id}")
def get_transformation(
    transformation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return transformation_controller.detail_payload(db, transformation_id)


@router.patch("/{transformation_id}")
def update_transformation(
    transformation_id: uuid.UUID,
    payload: TransformationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("transformation:write")),
) -> dict:
    transformation = transformation_service.get_transformation(db, transformation_id)
    sql_text = payload.sql_text or transformation.sql_text
    started = time.time()
    with ParseGuard(db, user, sql_text):
        transformation = transformation_service.update_transformation(
            db, user, transformation_id, payload.model_dump(exclude_unset=True)
        )
    ensure_not_timeout(time.time() - started)
    quota_service.consume(db, user)
    audit_logger.mark(
        request,
        action="AUDIT_SQL_CHANGED",
        entity_type="transformation",
        entity_id=transformation_id,
        payload={"sql_text": sql_text, "version": transformation.version},
    )
    return transformation_controller.detail_payload(db, transformation_id)


@router.post("/{transformation_id}/parse")
def reparse(
    transformation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("parse:run")),
) -> dict:
    transformation = transformation_service.get_transformation(db, transformation_id)
    started = time.time()
    with ParseGuard(db, user, transformation.sql_text):
        transformation = parse_service.parse_transformation(db, transformation)
    ensure_not_timeout(time.time() - started)
    quota_service.consume(db, user)
    audit_logger.mark(
        request,
        action="PARSE_RERUN",
        entity_type="transformation",
        entity_id=transformation_id,
        payload={"parse_status": transformation.parse_status},
    )
    return transformation_controller.detail_payload(db, transformation_id)


@router.post("/{transformation_id}/preview")
def preview(
    transformation_id: uuid.UUID,
    payload: ParseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("parse:run")),
) -> dict:
    transformation = transformation_service.get_transformation(db, transformation_id)
    sql_text = payload.sql_text or transformation.sql_text
    started = time.time()
    with ParseGuard(db, user, sql_text):
        result = transformation_controller.preview_payload(
            db,
            sql_text=sql_text,
            dialect=payload.dialect or transformation.dialect,
            output_asset_id=payload.output_asset_id or transformation.output_asset_id,
            input_asset_ids=payload.input_asset_ids_json
            or [uuid.UUID(str(x)) for x in (transformation.input_asset_ids_json or [])],
        )
    ensure_not_timeout(time.time() - started)
    return result


@router.post("/{transformation_id}/enqueue-parse")
def enqueue_parse(
    transformation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("parse:run")),
) -> dict:
    """把解析投递给 Celery worker（lineage 队列）；调用方轮询 /api/tasks/{task_id}。"""
    from worker.tasks import parse_tasks

    transformation_service.get_transformation(db, transformation_id)
    result = parse_tasks.parse_transformation_task.delay(str(transformation_id))
    log(logger, "WORKER_TASK_START", level=logging.INFO, task="parse_transformation", id=result.id)
    return {"task_id": result.id, "queue": "lineage", "status": "queued"}


@tasks_router.get("/{task_id}")
def task_status(task_id: str) -> dict:
    from worker.celery_app import celery_app

    async_result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": async_result.state,
        "ready": async_result.ready(),
        "result": async_result.result if async_result.ready() else None,
    }
