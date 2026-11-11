"""影响分析路由。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import impact_controller
from app.middlewares import audit_logger
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_capability
from app.models.user import User
from app.schemas.impact import ImpactRequest
from app.services import impact_service

router = APIRouter(prefix="/api/impact", tags=["impact"])


@router.post("/analyze")
def analyze(
    payload: ImpactRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_capability("impact:run")),
) -> dict:
    result = impact_controller.analyze_payload(
        db,
        user,
        target_asset_id=payload.target_asset_id,
        target_column=payload.target_column,
        change_type=payload.change_type,
        force=payload.force,
    )
    audit_logger.mark(
        request,
        action="AUDIT_IMPACT_REQUESTED",
        entity_type="impact_analysis",
        entity_id=result["id"],
        payload={
            "target_asset_id": str(payload.target_asset_id),
            "target_column": payload.target_column,
            "change_type": payload.change_type,
            "severity": result["severity"],
            "affected_count": result["affected_count"],
            "cached": result["cached"],
        },
    )
    return result


@router.get("/history")
def history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return impact_controller.history_payload(db, limit=limit)


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    analysis = impact_service.get_analysis(db, analysis_id)
    return {
        "id": str(analysis.id),
        "requested_by": str(analysis.requested_by),
        "change_type": analysis.change_type,
        "target_asset_id": str(analysis.target_asset_id),
        "target_column": analysis.target_column,
        "severity": analysis.severity,
        "affected_count": analysis.affected_count,
        "report_json": analysis.report_json,
        "created_at": analysis.created_at.isoformat(),
        "cached": False,
        "target_asset_name": (analysis.report_json or {}).get("target", {}).get("asset_name"),
    }
