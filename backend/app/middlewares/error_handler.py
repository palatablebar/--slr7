"""统一错误信封 {code, message, entity, field, request_id}。"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.constants.error_codes import E_INTERNAL, E_VALIDATION
from app.utils.errors import AppError

logger = logging.getLogger("datatrace.error")


def _envelope(code: str, message: str, *, entity=None, field=None, request_id=None, detail=None) -> dict:
    return {
        "code": code,
        "message": message,
        "entity": entity,
        "field": field,
        "request_id": request_id,
        "detail": detail or {},
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                exc.code,
                exc.message,
                entity=exc.entity,
                field=exc.field,
                request_id=request_id,
                detail=exc.detail,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", [])[1:]) or None
        return JSONResponse(
            status_code=422,
            content=_envelope(
                E_VALIDATION,
                first.get("msg", "请求参数不合法"),
                field=field,
                request_id=getattr(request.state, "request_id", None),
                detail={"errors": exc.errors()[:5]},
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db(request: Request, exc: SQLAlchemyError):
        logger.exception("database error")
        return JSONResponse(
            status_code=500,
            content=_envelope(
                E_INTERNAL, "数据库错误，请查看后端日志", request_id=getattr(request.state, "request_id", None)
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("unexpected error")
        return JSONResponse(
            status_code=500,
            content=_envelope(
                E_INTERNAL, f"{type(exc).__name__}", request_id=getattr(request.state, "request_id", None)
            ),
        )


def request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response
