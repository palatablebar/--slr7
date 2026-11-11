"""血缘控制器：响应包装。"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.services import lineage_service


def graph_payload(
    db: Session,
    *,
    asset_id: uuid.UUID,
    direction: str,
    depth: int,
    granularity: str,
    column: str | None,
) -> dict:
    return lineage_service.graph(
        db,
        asset_id=asset_id,
        direction=direction,
        depth=depth,
        granularity=granularity,
        column=column,
    )


def column_payload(db: Session, asset_id: uuid.UUID, column: str) -> dict:
    return lineage_service.column_lineage(db, asset_id, column)
