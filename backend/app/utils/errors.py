"""统一业务异常。"""
from __future__ import annotations

from typing import Any

from app.constants.error_codes import ERROR_MESSAGES


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        status_code: int | None = None,
        entity: str | None = None,
        field: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, code)
        self.status_code = status_code or _default_status(code)
        self.entity = entity
        self.field = field
        self.detail = detail or {}
        super().__init__(self.message)


def _default_status(code: str) -> int:
    return {
        "E_UNAUTHORIZED": 401,
        "E_FORBIDDEN": 403,
        "E_NOT_FOUND": 404,
        "E_VALIDATION": 422,
        "E_PARSE_FAILED": 422,
        "E_PARSE_TIMEOUT": 504,
        "E_PARSE_QUOTA": 429,
        "E_ASSET_IN_USE": 409,
        "E_CYCLE_UNRESOLVED": 409,
        "E_CONFLICT": 409,
    }.get(code, 400)
