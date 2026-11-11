"""DataTrace 后端入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import init_db
from app.config.logging import configure_logging
from app.config.settings import settings
from app.middlewares.audit_logger import AuditMiddleware
from app.middlewares.error_handler import register_error_handlers, request_id_middleware
from app.routes import assets, audit, auth, health, impact, lineage, quota, transformations
from app.worker_bridge import enqueue_self_seed

configure_logging()
logger = logging.getLogger("datatrace.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_demo:
        enqueue_self_seed()
    logger.info("DataTrace backend ready (seed_demo=%s)", settings.seed_demo)
    yield


app = FastAPI(
    title="DataTrace API",
    description="列级数据血缘与影响分析平台",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)
request_id_middleware(app)
register_error_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(transformations.router)
app.include_router(transformations.tasks_router)
app.include_router(lineage.router)
app.include_router(impact.router)
app.include_router(quota.router)
app.include_router(audit.router)
