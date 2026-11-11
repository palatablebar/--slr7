"""配额 schema。"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    max_sql_bytes: int
    max_concurrent_parses: int
    parses_used: int
    window_start: datetime
    remaining: int = 0
