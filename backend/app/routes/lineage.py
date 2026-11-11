"""血缘路由。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import lineage_controller
from app.middlewares.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/lineage", tags=["lineage"])


@router.get("/graph")
def get_graph(
    asset_id: uuid.UUID = Query(...),
    direction: str = Query(default="both"),
    depth: int = Query(default=3, ge=1, le=4),
    granularity: str = Query(default="asset"),
    column: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return lineage_controller.graph_payload(
        db, asset_id=asset_id, direction=direction, depth=depth, granularity=granularity, column=column
    )


@router.get("/column")
def get_column(
    asset_id: uuid.UUID = Query(...),
    column: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return lineage_controller.column_payload(db, asset_id, column)
