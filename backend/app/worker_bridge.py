"""启动期执行 seed（失败只记日志，不阻塞启动，容器仍须 healthy）。"""
from __future__ import annotations

import logging

from app.constants import log_templates
from app.utils.logger import log

logger = logging.getLogger("datatrace.seed")


def enqueue_self_seed() -> None:
    try:
        from scripts.seed_demo import run_seed

        summary = run_seed()
        log(
            logger,
            "SEED_DONE",
            level=logging.INFO,
            users=summary.get("users"),
            assets=summary.get("assets"),
            transformations=summary.get("transformations"),
            edges=summary.get("edges"),
        )
    except Exception as exc:  # pragma: no cover - 生产可关闭 seed
        log(logger, "SEED_FAILED", level=logging.WARNING, error=str(exc))
        logger.warning("seed demo failed but backend keeps running", exc_info=True)
