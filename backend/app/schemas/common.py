"""公共 schema：错误信封、分页。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    entity: str | None = None
    field: str | None = None
    request_id: str | None = None
    detail: dict[str, Any] | None = None


class Page(BaseModel):
    items: list[Any]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class MessageOut(BaseModel):
    message: str
    code: str = "OK"
