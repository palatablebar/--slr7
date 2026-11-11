"""数据资产 schema。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssetTypeLiteral = Literal["table", "view", "materialized_view", "cte_result"]
AssetStatusLiteral = Literal["active", "deprecated", "draft"]


class AssetColumnIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    data_type: str | None = Field(default=None, max_length=64)
    nullable: bool | None = True
    ordinal: int | None = None
    description: str | None = None


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    asset_type: AssetTypeLiteral = "table"
    database_name: str = Field(default="lanzo_dw", max_length=64)
    schema_name: str = Field(min_length=1, max_length=64)
    columns_json: list[AssetColumnIn] = Field(default_factory=list)
    description: str | None = None
    status: AssetStatusLiteral = "active"


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    asset_type: AssetTypeLiteral | None = None
    columns_json: list[AssetColumnIn] | None = None
    description: str | None = None
    status: AssetStatusLiteral | None = None


class ColumnStat(BaseModel):
    name: str
    data_type: str | None = None
    nullable: bool | None = True
    ordinal: int | None = None
    description: str | None = None
    upstream_count: int = 0
    downstream_count: int = 0


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    asset_type: AssetTypeLiteral
    database_name: str
    schema_name: str
    description: str | None = None
    status: AssetStatusLiteral
    updated_at: datetime
    column_count: int = 0
    display_name: str = ""
    full_name: str = ""


class AssetDetail(AssetOut):
    columns: list[ColumnStat] = Field(default_factory=list)
    owner_display_name: str | None = None
    upstream_assets: list[dict] = Field(default_factory=list)
    downstream_assets: list[dict] = Field(default_factory=list)
    producer_transformations: list[dict] = Field(default_factory=list)
    consumer_transformations: list[dict] = Field(default_factory=list)
    schema_changes: list[dict] = Field(default_factory=list)
    recent_audits: list[dict] = Field(default_factory=list)
