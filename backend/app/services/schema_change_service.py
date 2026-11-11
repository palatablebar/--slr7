"""结构变更事件记录。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.constants import log_templates
from app.models.data_asset import DataAsset
from app.models.schema_change_event import SchemaChangeEvent
from app.utils.logger import log

import logging

logger = logging.getLogger("datatrace.schema_change")


def record(
    db: Session,
    asset: DataAsset,
    change_type: str,
    column_name: str,
    old_type: str | None = None,
    new_type: str | None = None,
    source: str = "manual",
) -> SchemaChangeEvent:
    event = SchemaChangeEvent(
        asset_id=asset.id,
        change_type=change_type,
        column_name=column_name,
        old_type=old_type,
        new_type=new_type,
        source=source,
    )
    db.add(event)
    db.flush()
    log(
        logger,
        "SCHEMA_CHANGE_RECORDED",
        level=logging.INFO,
        asset=asset.full_name,
        column=column_name,
        change_type=change_type,
        old=old_type,
        new=new_type,
    )
    return event


def diff_columns(old_columns: list[dict], new_columns: list[dict]) -> list[dict]:
    """对比列清单，产出需要记录的变更事件描述。"""
    old_map = {c.get("name"): c for c in old_columns or []}
    new_map = {c.get("name"): c for c in new_columns or []}
    changes: list[dict] = []
    for name, new_col in new_map.items():
        if name not in old_map:
            changes.append(
                {
                    "change_type": "add_column",
                    "column_name": name,
                    "old_type": None,
                    "new_type": new_col.get("data_type"),
                }
            )
        else:
            old_type = old_map[name].get("data_type")
            new_type = new_col.get("data_type")
            if (old_type or "") != (new_type or ""):
                changes.append(
                    {
                        "change_type": "change_type",
                        "column_name": name,
                        "old_type": old_type,
                        "new_type": new_type,
                    }
                )
    for name, old_col in old_map.items():
        if name not in new_map:
            changes.append(
                {
                    "change_type": "drop_column",
                    "column_name": name,
                    "old_type": old_col.get("data_type"),
                    "new_type": None,
                }
            )
    return changes


def list_for_asset(db: Session, asset_id) -> list[SchemaChangeEvent]:
    return (
        db.query(SchemaChangeEvent)
        .filter(SchemaChangeEvent.asset_id == asset_id)
        .order_by(SchemaChangeEvent.detected_at.desc())
        .all()
    )
