"""Celery 应用：lineage / impact 两个队列，超时与重试。"""
from __future__ import annotations

from celery import Celery

from app.config.settings import settings

celery_app = Celery(
    "datatrace",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks.parse_tasks", "worker.tasks.impact_tasks"],
)

celery_app.conf.update(
    task_default_queue="lineage",
    task_routes={
        "worker.tasks.parse_tasks.*": {"queue": "lineage"},
        "worker.tasks.impact_tasks.*": {"queue": "impact"},
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=25,
    task_time_limit=40,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
)
