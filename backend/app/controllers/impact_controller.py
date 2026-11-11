"""影响分析控制器：响应包装。"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import impact_service


def analyze_payload(
    db: Session,
    user: User,
    *,
    target_asset_id: uuid.UUID,
    target_column: str | None,
    change_type: str,
    force: bool,
) -> dict:
    analysis, cached = impact_service.analyze(
        db,
        user,
        target_asset_id=target_asset_id,
        target_column=target_column,
        change_type=change_type,
        force=force,
    )
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
        "cached": cached,
        "target_asset_name": (analysis.report_json or {}).get("target", {}).get("asset_name"),
    }


def history_payload(db: Session, limit: int = 20) -> dict:
    items = impact_service.history(db, limit=limit)
    return {"items": items, "total": len(items)}
