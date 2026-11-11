"""环检测服务：列级图上的 Tarjan 强连通分量 + 资产级环边标记。"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.constants import log_templates
from app.models.data_asset import DataAsset
from app.models.lineage_edge import LineageEdge
from app.parsers.graph import build_adjacency, find_cycles
from app.utils.logger import log

logger = logging.getLogger("datatrace.cycle")


def detect_cycles(db: Session) -> tuple[list[dict], set[tuple[str, str]]]:
    """返回 (cycles, cycle_edge_pairs)；cycle_edge_pairs 为资产级 (source_asset, target_asset)。"""
    edges = db.query(LineageEdge).all()
    payload = [
        {
            "source_asset_id": str(edge.source_asset_id),
            "source_column": edge.source_column,
            "target_asset_id": str(edge.target_asset_id),
            "target_column": edge.target_column,
        }
        for edge in edges
    ]
    adjacency = build_adjacency(payload)
    cycles = find_cycles(adjacency)
    if cycles:
        log(logger, "CYCLE_DETECTED", level=logging.WARNING, components=len(cycles), sample=str(cycles[0])[:300])

    asset_map = {str(asset.id): asset.display_name for asset in db.query(DataAsset).all()}
    formatted = []
    cycle_pairs: set[tuple[str, str]] = set()
    for cycle in cycles:
        nodes = [
            {
                "asset_id": node["asset_id"],
                "asset_name": asset_map.get(node["asset_id"], node["asset_id"][:8]),
                "column": node["column"],
            }
            for node in cycle["nodes"]
        ]
        path = [
            {
                "asset_id": node["asset_id"],
                "asset_name": asset_map.get(node["asset_id"], node["asset_id"][:8]),
                "column": node["column"],
            }
            for node in cycle["sample_path"]
        ]
        formatted.append({"nodes": nodes, "sample_path": path, "kind": "column"})
        for index in range(len(path) - 1):
            cycle_pairs.add((path[index]["asset_id"], path[index + 1]["asset_id"]))
    return formatted, cycle_pairs
