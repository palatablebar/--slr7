"""血缘边类型枚举。"""
from enum import Enum


class EdgeKind(str, Enum):
    direct = "direct"
    derived = "derived"
    aggregate = "aggregate"
    join_key = "join_key"


EDGE_KIND_LABELS = {
    EdgeKind.direct: "直传",
    EdgeKind.derived: "派生",
    EdgeKind.aggregate: "聚合",
    EdgeKind.join_key: "关联键",
}

# 同一条 (transformation, source_column, target_column) 只保留优先级最高的边类型
EDGE_KIND_PRIORITY = {
    EdgeKind.direct: 1,
    EdgeKind.join_key: 2,
    EdgeKind.derived: 3,
    EdgeKind.aggregate: 4,
}
