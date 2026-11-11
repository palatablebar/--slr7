"""血缘图 schema。"""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

DirectionLiteral = Literal["upstream", "downstream", "both"]


class GraphNode(BaseModel):
    id: str
    asset_id: str
    asset_name: str
    asset_type: str
    column: str | None = None
    depth: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_kind: str
    source_column: str
    target_column: str
    transformation_id: str
    transformation_name: str
    expression_text: str | None = None
    in_cycle: bool = False
    parse_status: str = "parsed"


class LineageGraphOut(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    cycle_edges: list[dict] = Field(default_factory=list)
    depth: int = 3
    direction: DirectionLiteral = "both"
    truncated: bool = False
    asset_nodes: list[dict] = Field(default_factory=list)


class ColumnLineageOut(BaseModel):
    asset_id: uuid.UUID
    column: str
    upstream: list[dict] = Field(default_factory=list)
    downstream: list[dict] = Field(default_factory=list)
