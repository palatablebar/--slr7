"""影响分析严重度与规则常量。"""
from enum import Enum


class ImpactSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


SEVERITY_LABELS = {
    ImpactSeverity.low: "低",
    ImpactSeverity.medium: "中",
    ImpactSeverity.high: "高",
    ImpactSeverity.critical: "严重",
}

SEVERITY_ORDER = {
    ImpactSeverity.low: 0,
    ImpactSeverity.medium: 1,
    ImpactSeverity.high: 2,
    ImpactSeverity.critical: 3,
}

# 显式定级规则表：以“最小传播深度”（最直接下游）定级
DEPTH_SEVERITY_RULES = [
    (1, ImpactSeverity.high),
    (3, ImpactSeverity.medium),
    (12, ImpactSeverity.low),
]
