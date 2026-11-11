"""血缘图服务：资产级/列级图遍历、方向与深度、环标记。"""
from __future__ import annotations

import uuid
from collections import deque

from sqlalchemy.orm import Session

from app.constants.error_codes import E_NOT_FOUND
from app.constants.lineage import MAX_GRAPH_DEPTH, LineageDirection
from app.models.data_asset import DataAsset
from app.models.lineage_edge import LineageEdge
from app.models.transformation import Transformation
from app.services import cycle_service
from app.utils.errors import AppError


def _load(db: Session):
    assets = {str(asset.id): asset for asset in db.query(DataAsset).all()}
    transformations = {str(t.id): t for t in db.query(Transformation).all()}
    edges = db.query(LineageEdge).order_by(LineageEdge.id).all()
    return assets, transformations, edges


def graph(
    db: Session,
    *,
    asset_id: uuid.UUID,
    direction: str = "both",
    depth: int = 3,
    granularity: str = "asset",
    column: str | None = None,
) -> dict:
    assets, transformations, edges = _load(db)
    if str(asset_id) not in assets:
        raise AppError(E_NOT_FOUND, "资产不存在", entity="data_asset", field="asset_id")
    try:
        direction_enum = LineageDirection(direction)
    except ValueError:
        direction_enum = LineageDirection.both
    depth = max(1, min(int(depth or 3), MAX_GRAPH_DEPTH))
    start_asset = assets[str(asset_id)]
    cycles, cycle_pairs = cycle_service.detect_cycles(db)

    if granularity == "column":
        nodes, graph_edges = _column_graph(
            assets, transformations, edges, str(asset_id), column, direction_enum, depth
        )
    else:
        nodes, graph_edges = _asset_graph(
            assets, transformations, edges, str(asset_id), direction_enum, depth, cycle_pairs
        )

    return {
        "nodes": nodes,
        "edges": graph_edges,
        "cycle_edges": [
            {
                "source": pair[0],
                "target": pair[1],
                "reason": "列级血缘存在环",
            }
            for pair in cycle_pairs
        ],
        "cycles": cycles,
        "depth": depth,
        "direction": direction_enum.value,
        "granularity": granularity,
        "truncated": False,
        "start_asset": {
            "id": str(start_asset.id),
            "name": start_asset.display_name,
            "asset_type": start_asset.asset_type,
        },
        "asset_nodes": [
            {
                "id": str(asset.id),
                "name": asset.display_name,
                "asset_type": asset.asset_type,
                "status": asset.status,
                "column_count": len(asset.columns_json or []),
            }
            for asset in assets.values()
        ],
    }


def _asset_graph(assets, transformations, edges, start: str, direction: LineageDirection, depth: int, cycle_pairs):
    adjacency: dict[str, list[dict]] = {}
    for edge in edges:
        source = str(edge.source_asset_id)
        target = str(edge.target_asset_id)
        adjacency.setdefault(source, []).append(
            {"target": target, "edge": edge, "direction": "downstream"}
        )
        adjacency.setdefault(target, []).append(
            {"target": source, "edge": edge, "direction": "upstream"}
        )

    visited: dict[str, int] = {start: 0}
    # layer：下游为正、上游为负（布局时把上游放在起点左侧）
    layers: dict[str, int] = {start: 0}
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for link in adjacency.get(current, []):
            if direction == LineageDirection.upstream and link["direction"] != "upstream":
                continue
            if direction == LineageDirection.downstream and link["direction"] != "downstream":
                continue
            neighbor = link["target"]
            if neighbor not in visited:
                visited[neighbor] = current_depth + 1
                layers[neighbor] = layers.get(current, 0) + (
                    -1 if link["direction"] == "upstream" else 1
                )
                queue.append((neighbor, current_depth + 1))

    nodes = []
    for asset_key, node_depth in visited.items():
        asset = assets.get(asset_key)
        if asset is None:
            continue
        nodes.append(
            {
                "id": asset_key,
                "asset_id": asset_key,
                "asset_name": asset.display_name,
                "asset_type": asset.asset_type,
                "status": asset.status,
                "depth": node_depth,
                "layer": layers.get(asset_key, node_depth),
                "column_count": len(asset.columns_json or []),
            }
        )
    nodes.sort(key=lambda item: (item["layer"], item["asset_name"]))

    graph_edges = []
    seen_pairs: dict[tuple[str, str], dict] = {}
    for edge in edges:
        source = str(edge.source_asset_id)
        target = str(edge.target_asset_id)
        if source not in visited or target not in visited:
            continue
        key = (source, target)
        transformation = transformations.get(str(edge.transformation_id))
        if key in seen_pairs:
            seen_pairs[key]["edge_count"] += 1
            continue
        seen_pairs[key] = {
            "id": f"e{edge.id}",
            "source": source,
            "target": target,
            "source_name": assets[source].display_name if source in assets else source,
            "target_name": assets[target].display_name if target in assets else target,
            "edge_kind": edge.edge_kind,
            "source_column": edge.source_column,
            "target_column": edge.target_column,
            "transformation_id": str(edge.transformation_id),
            "transformation_name": transformation.name if transformation else "",
            "parse_status": transformation.parse_status if transformation else "parsed",
            "expression_text": edge.expression_text,
            "in_cycle": (source, target) in cycle_pairs,
            "edge_count": 1,
        }
    graph_edges = list(seen_pairs.values())
    return nodes, graph_edges


def _column_graph(assets, transformations, edges, start_asset: str, column, direction: LineageDirection, depth: int):
    def node_id(asset: str, col: str) -> str:
        return f"{asset}::{col}"

    adjacency: dict[str, list[dict]] = {}
    for edge in edges:
        source = node_id(str(edge.source_asset_id), edge.source_column)
        target = node_id(str(edge.target_asset_id), edge.target_column)
        adjacency.setdefault(source, []).append(
            {"target": target, "edge": edge, "direction": "downstream", "node": target}
        )
        adjacency.setdefault(target, []).append(
            {"target": source, "edge": edge, "direction": "upstream", "node": source}
        )

    starts = []
    if column:
        identity = node_id(start_asset, column)
        starts = [identity] if identity in adjacency else []
        if not starts:
            # 该列还没有任何边，仍然把起点画出来
            starts = [identity]
            adjacency.setdefault(identity, [])
    else:
        starts = [nid for nid in adjacency if nid.startswith(start_asset + "::")]
        if not starts:
            starts = []

    visited: dict[str, int] = {node: 0 for node in starts}
    queue: deque[tuple[str, int]] = deque((node, 0) for node in starts)
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for link in adjacency.get(current, []):
            if direction == LineageDirection.upstream and link["direction"] != "upstream":
                continue
            if direction == LineageDirection.downstream and link["direction"] != "downstream":
                continue
            neighbor = link["target"]
            if neighbor not in visited:
                visited[neighbor] = current_depth + 1
                queue.append((neighbor, current_depth + 1))

    nodes = []
    for nid, node_depth in visited.items():
        asset_id, _, col = nid.partition("::")
        asset = assets.get(asset_id)
        nodes.append(
            {
                "id": nid,
                "asset_id": asset_id,
                "asset_name": asset.display_name if asset else asset_id[:8],
                "asset_type": asset.asset_type if asset else "table",
                "column": col,
                "depth": node_depth,
            }
        )
    nodes.sort(key=lambda item: (item["depth"], item["asset_name"], item["column"]))

    graph_edges = []
    for edge in edges:
        source = node_id(str(edge.source_asset_id), edge.source_column)
        target = node_id(str(edge.target_asset_id), edge.target_column)
        if source not in visited or target not in visited:
            continue
        transformation = transformations.get(str(edge.transformation_id))
        graph_edges.append(
            {
                "id": f"e{edge.id}",
                "source": source,
                "target": target,
                "edge_kind": edge.edge_kind,
                "source_column": edge.source_column,
                "target_column": edge.target_column,
                "transformation_id": str(edge.transformation_id),
                "transformation_name": transformation.name if transformation else "",
                "parse_status": transformation.parse_status if transformation else "parsed",
                "expression_text": edge.expression_text,
                "in_cycle": False,
            }
        )
    return nodes, graph_edges


def column_lineage(db: Session, asset_id: uuid.UUID, column: str) -> dict:
    edges = (
        db.query(LineageEdge)
        .filter(
            (LineageEdge.source_asset_id == asset_id) & (LineageEdge.source_column == column)
            | (LineageEdge.target_asset_id == asset_id) & (LineageEdge.target_column == column)
        )
        .all()
    )
    assets = {str(a.id): a for a in db.query(DataAsset).all()}
    transformations = {str(t.id): t for t in db.query(Transformation).all()}
    upstream = []
    downstream = []
    for edge in edges:
        kind = edge.edge_kind
        transformation = transformations.get(str(edge.transformation_id))
        item = {
            "edge_kind": kind,
            "expression_text": edge.expression_text,
            "transformation_id": str(edge.transformation_id),
            "transformation_name": transformation.name if transformation else "",
            "parse_status": transformation.parse_status if transformation else "parsed",
            "source_asset_id": str(edge.source_asset_id),
            "source_asset_name": assets[str(edge.source_asset_id)].display_name
            if str(edge.source_asset_id) in assets
            else "",
            "source_column": edge.source_column,
            "target_asset_id": str(edge.target_asset_id),
            "target_asset_name": assets[str(edge.target_asset_id)].display_name
            if str(edge.target_asset_id) in assets
            else "",
            "target_column": edge.target_column,
        }
        if str(edge.target_asset_id) == str(asset_id) and edge.target_column == column:
            upstream.append(item)
        if str(edge.source_asset_id) == str(asset_id) and edge.source_column == column:
            downstream.append(item)
    return {
        "asset_id": str(asset_id),
        "column": column,
        "upstream": upstream,
        "downstream": downstream,
    }
