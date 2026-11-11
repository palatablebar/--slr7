"""血缘方向与图遍历常量。"""
from enum import Enum


class LineageDirection(str, Enum):
    upstream = "upstream"
    downstream = "downstream"
    both = "both"


DIRECTION_LABELS = {
    LineageDirection.upstream: "上游",
    LineageDirection.downstream: "下游",
    LineageDirection.both: "双向",
}

MAX_GRAPH_DEPTH = 4
MAX_IMPACT_DEPTH = 12
