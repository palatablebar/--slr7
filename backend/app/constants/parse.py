"""解析状态枚举。"""
from enum import Enum


class ParseStatus(str, Enum):
    pending = "pending"
    parsed = "parsed"
    partial = "partial"
    failed = "failed"


PARSE_STATUS_LABELS = {
    ParseStatus.pending: "待解析",
    ParseStatus.parsed: "解析完成",
    ParseStatus.partial: "部分解析",
    ParseStatus.failed: "解析失败",
}
