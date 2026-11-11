"""影响分析 schema。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ChangeTypeLiteral = Literal["add_column", "drop_column", "rename_column", "change_type"]
SeverityLiteral = Literal["low", "medium", "high", "critical"]


class ImpactRequest(BaseModel):
    target_asset_id: uuid.UUID
    target_column: str | None = Field(default=None, max_length=128)
    change_type: ChangeTypeLiteral
    force: bool = False


class ImpactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requested_by: uuid.UUID
    change_type: ChangeTypeLiteral
    target_asset_id: uuid.UUID
    target_column: str | None = None
    severity: SeverityLiteral
    affected_count: int
    report_json: dict = Field(default_factory=dict)
    created_at: datetime
    cached: bool = False
    target_asset_name: str | None = None
