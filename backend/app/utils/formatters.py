"""多职责格式化：严重度中文名、资产全名、边类型标签、SQL 片段截断。"""
from __future__ import annotations

from app.constants.asset import ASSET_TYPE_LABELS, AssetType
from app.constants.change import CHANGE_TYPE_LABELS
from app.constants.edge import EDGE_KIND_LABELS, EdgeKind
from app.constants.impact import SEVERITY_LABELS, ImpactSeverity
from app.constants.parse import PARSE_STATUS_LABELS, ParseStatus
from app.utils.hashing import truncate


def severity_label(severity: str) -> str:
    try:
        return SEVERITY_LABELS[ImpactSeverity(severity)]
    except ValueError:
        return severity


def asset_full_name(asset) -> str:
    return f"{asset.database_name}.{asset.schema_name}.{asset.name}"


def asset_display_name(asset) -> str:
    return f"{asset.schema_name}.{asset.name}"


def edge_kind_label(kind: str) -> str:
    try:
        return EDGE_KIND_LABELS[EdgeKind(kind)]
    except ValueError:
        return kind


def parse_status_label(status: str) -> str:
    try:
        return PARSE_STATUS_LABELS[ParseStatus(status)]
    except ValueError:
        return status


def asset_type_label(asset_type: str) -> str:
    try:
        return ASSET_TYPE_LABELS[AssetType(asset_type)]
    except ValueError:
        return asset_type


def change_type_label(change_type: str) -> str:
    try:
        return CHANGE_TYPE_LABELS[change_type]
    except (ValueError, KeyError):
        return change_type


def sql_snippet(sql_text: str, column_name: str, radius: int = 90) -> str:
    """在 SQL 文本里定位列名并截取最小上下文片段。"""
    if not sql_text or not column_name:
        return truncate(sql_text, 160)
    idx = sql_text.lower().find(column_name.lower())
    if idx < 0:
        return truncate(sql_text, 160)
    start = max(0, idx - radius)
    end = min(len(sql_text), idx + len(column_name) + radius)
    snippet = sql_text[start:end].strip()
    return truncate(("…" if start > 0 else "") + snippet + ("…" if end < len(sql_text) else ""), 512)
