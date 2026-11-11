"""转换控制器：响应包装。"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import parse_service, transformation_service
from app.utils.formatters import parse_status_label


def list_payload(db: Session) -> dict:
    items = transformation_service.list_transformations(db)
    for item in items:
        item["parse_status_label"] = parse_status_label(item["parse_status"])
    return {"items": items, "total": len(items)}


def detail_payload(db: Session, transformation_id: uuid.UUID) -> dict:
    detail = transformation_service.get_detail(db, transformation_id)
    detail["parse_status_label"] = parse_status_label(detail["parse_status"])
    return detail


def preview_payload(db: Session, *, sql_text: str, dialect: str, output_asset_id, input_asset_ids) -> dict:
    result = parse_service.preview(db, sql_text, dialect, output_asset_id, input_asset_ids)
    return {
        "parse_status": result.status,
        "parse_error": result.parse_error,
        "error_line": result.error_line,
        "error_column": result.error_column,
        "warnings": result.warnings,
        "unresolved": result.unresolved,
        "columns": [
            {
                "target_column": target,
                "sources": [
                    {"asset_id": ref.asset_id, "column": ref.column, "edge_kind": ref.kind}
                    for ref in refs
                ],
            }
            for target, refs in result.columns.items()
        ],
        "report": {"edge_count": result.edge_count, "star_expanded": result.star_expanded},
    }
