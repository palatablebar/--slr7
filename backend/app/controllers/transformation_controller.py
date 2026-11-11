"""转换控制器：响应包装。"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.constants.messages import MSG_DRAFT_PROMOTED, MSG_DRAFT_SAVED_FAILED
from app.models.user import User
from app.services import parse_service, transformation_service
from app.utils.formatters import parse_status_label


def list_payload(db: Session) -> dict:
    items = transformation_service.list_transformations(db)
    for item in items:
        item["parse_status_label"] = parse_status_label(item["parse_status"])
        if item.get("draft"):
            item["draft"]["parse_status_label"] = parse_status_label(item["draft"]["parse_status"])
    return {"items": items, "total": len(items)}


def detail_payload(db: Session, transformation_id: uuid.UUID) -> dict:
    detail = transformation_service.get_detail(db, transformation_id)
    detail["parse_status_label"] = parse_status_label(detail["parse_status"])
    if detail.get("draft"):
        detail["draft"]["parse_status_label"] = parse_status_label(detail["draft"]["parse_status"])
    return detail


def save_draft_payload(
    db: Session, user: User, transformation_id: uuid.UUID, payload: dict
) -> dict:
    """保存草稿并校验。

    解析失败不抛 HTTP 错误：HTTP 200 + promoted=False，错误细节放在
    draft.parse_error 里，前端明确提示且继续展示已上线血缘。
    """
    transformation, draft = transformation_service.save_draft(db, user, transformation_id, payload)
    detail = detail_payload(db, transformation.id)
    if draft is None:
        return {
            "promoted": True,
            "message": MSG_DRAFT_PROMOTED,
            "transformation": detail,
        }
    return {
        "promoted": False,
        "message": MSG_DRAFT_SAVED_FAILED,
        "transformation": detail,
    }


def discard_draft_payload(db: Session, user: User, transformation_id: uuid.UUID) -> dict:
    transformation = transformation_service.discard_draft(db, user, transformation_id)
    return detail_payload(db, transformation.id)


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
