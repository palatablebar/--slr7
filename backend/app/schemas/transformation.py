"""转换 schema。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ParseStatusLiteral = Literal["pending", "parsed", "partial", "failed"]


class TransformationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    dialect: str = Field(default="postgres", max_length=24)
    sql_text: str = Field(min_length=1)
    input_asset_ids_json: list[uuid.UUID] = Field(min_length=1)
    output_asset_id: uuid.UUID


class TransformationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    dialect: str | None = Field(default=None, max_length=24)
    sql_text: str | None = None
    input_asset_ids_json: list[uuid.UUID] | None = None
    output_asset_id: uuid.UUID | None = None


class TransformationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    dialect: str
    sql_text: str
    input_asset_ids_json: list
    output_asset_id: uuid.UUID
    parse_status: ParseStatusLiteral
    parse_error: str | None = None
    report_json: dict = Field(default_factory=dict)
    version: int
    updated_at: datetime
    output_asset_name: str | None = None
    owner_display_name: str | None = None
    edge_count: int = 0
    has_draft: bool = False
    draft: "TransformationDraftOut | None" = None


class TransformationDraftOut(BaseModel):
    """未上线草稿：状态只代表草稿本身，不代表已上线版本。"""

    id: uuid.UUID
    sql_text: str
    dialect: str
    input_asset_ids_json: list
    output_asset_id: uuid.UUID
    parse_status: ParseStatusLiteral
    parse_error: str | None = None
    error_line: int | None = None
    error_column: int | None = None
    report_json: dict = Field(default_factory=dict)
    updated_at: datetime


class TransformationDetail(TransformationOut):
    input_assets: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class DraftSaveResult(BaseModel):
    """保存草稿的结果：promoted=False 时上线血缘未变，错误在 draft 中。"""

    promoted: bool
    message: str
    transformation: TransformationDetail


class ParseRequest(BaseModel):
    sql_text: str | None = None
    dialect: str | None = None
    output_asset_id: uuid.UUID | None = None
    input_asset_ids_json: list[uuid.UUID] | None = None


class ParsePreviewOut(BaseModel):
    parse_status: ParseStatusLiteral
    parse_error: str | None = None
    error_line: int | None = None
    error_column: int | None = None
    report: dict = Field(default_factory=dict)
    columns: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unresolved: list[dict] = Field(default_factory=list)
