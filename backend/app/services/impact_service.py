"""影响分析服务：可达性 BFS + 严重度定级 + 迁移清单（真实计算，落库为快照）。"""
from __future__ import annotations

import logging
import uuid
from collections import deque

from sqlalchemy.orm import Session

from app.constants import log_templates
from app.constants.asset import REPORT_EXCLUDED_ASSET_TYPES, AssetType
from app.constants.change import ChangeType
from app.constants.error_codes import E_NOT_FOUND
from app.constants.impact import SEVERITY_ORDER, ImpactSeverity
from app.constants.lineage import MAX_IMPACT_DEPTH
from app.models.data_asset import DataAsset
from app.models.impact_analysis import ImpactAnalysis
from app.models.lineage_edge import LineageEdge
from app.models.transformation import Transformation
from app.models.user import User
from app.parsers.graph import build_adjacency, find_cycles, reachable
from app.utils.errors import AppError
from app.utils.logger import log

logger = logging.getLogger("datatrace.impact")


def _severity_from_depth(min_depth: int | None) -> ImpactSeverity:
    if min_depth is None:
        return ImpactSeverity.low
    if min_depth <= 1:
        return ImpactSeverity.high
    if min_depth <= 3:
        return ImpactSeverity.medium
    return ImpactSeverity.low


def _upgrade(severity: ImpactSeverity) -> ImpactSeverity:
    order = [ImpactSeverity.low, ImpactSeverity.medium, ImpactSeverity.high, ImpactSeverity.critical]
    index = order.index(severity)
    return order[min(index + 1, len(order) - 1)]


def grade_severity(
    *,
    min_depth: int | None,
    change_type: str,
    has_materialized_view: bool,
    has_cycle: bool,
) -> ImpactSeverity:
    """显式定级规则表（README 同步）：
    1) depth==1→high；2..3→medium；>=4→low
    2) 命中 materialized_view 升一级
    3) 命中环 → critical
    4) change_type==drop_column 升一级（上限 critical）
    """
    severity = _severity_from_depth(min_depth)
    if has_materialized_view:
        severity = _upgrade(severity)
    if has_cycle:
        severity = ImpactSeverity.critical
    if change_type == ChangeType.drop_column.value:
        severity = _upgrade(severity)
    return severity


def _suggest_action(change_type: str, edge_kind: str, asset: DataAsset) -> tuple[str, str]:
    """返回 (action, reason)。"""
    is_mv = asset.asset_type == AssetType.materialized_view.value
    if change_type == ChangeType.drop_column.value:
        if is_mv:
            return "refresh_mv", "物化视图依赖该列，删除后必须重建/刷新物化视图"
        return "drop_downstream", "下游仍引用该列，删除前需先移除下游引用"
    if is_mv:
        return "refresh_mv", "物化视图的列定义需要随上游变更刷新"
    if change_type in (ChangeType.change_type.value,):
        if edge_kind in ("aggregate", "derived"):
            return "add_cast", "下游在该列上做了聚合/表达式计算，需要显式类型转换后再计算"
        return "rewrite_sql", "下游直接引用该列，改类型后需要重写 SELECT 表达式"
    if change_type == ChangeType.rename_column.value:
        return "rewrite_sql", "列被重命名，下游 SQL 需要同步改列名"
    return "rewrite_sql", "上游新增列后下游需要确认 SELECT * 与列顺序"


def _suggested_sql(action: str, asset: DataAsset, column: str, change_type: str) -> str:
    ref = f"{asset.display_name}.{column}"
    if action == "add_cast":
        return f"CAST({column} AS numeric(18,2))  -- {ref}：在聚合/表达式前显式转型"
    if action == "drop_downstream":
        return f"-- 从 SELECT 中移除 {column}，再重新解析该转换 -- {ref}"
    if action == "refresh_mv":
        return f"REFRESH MATERIALIZED VIEW {asset.schema_name}.{asset.name};"
    return f"-- 重写引用 {ref} 的 SELECT 表达式，并重新解析该转换"


def _build_checklist(
    affected: list[dict],
    assets: dict[str, DataAsset],
    change_type: str,
) -> list[dict]:
    checklist = []
    for node in affected:
        asset = assets.get(node["asset_id"])
        if asset is None:
            continue
        if asset.asset_type in {t.value for t in REPORT_EXCLUDED_ASSET_TYPES}:
            continue
        if asset.status != "active":
            continue
        action, reason = _suggest_action(change_type, node["edge_kind"], asset)
        checklist.append(
            {
                "asset_id": node["asset_id"],
                "asset_name": asset.display_name,
                "column": node["column"],
                "action": action,
                "suggested_sql": _suggested_sql(action, asset, node["column"], change_type),
                "reason": reason,
                "severity": node["severity"],
                "depth": node["depth"],
            }
        )
    checklist.sort(key=lambda item: (-SEVERITY_ORDER[ImpactSeverity(item["severity"])], item["depth"]))
    return checklist


def analyze(
    db: Session,
    user: User,
    *,
    target_asset_id: uuid.UUID,
    target_column: str | None,
    change_type: str,
    force: bool = False,
) -> tuple[ImpactAnalysis, bool]:
    asset = db.get(DataAsset, target_asset_id)
    if asset is None:
        raise AppError(E_NOT_FOUND, "目标资产不存在", entity="data_asset", field="target_asset_id")

    cached = (
        db.query(ImpactAnalysis)
        .filter(
            ImpactAnalysis.target_asset_id == target_asset_id,
            ImpactAnalysis.target_column == target_column,
            ImpactAnalysis.change_type == change_type,
        )
        .order_by(ImpactAnalysis.created_at.desc())
        .first()
    )
    if cached is not None and not force:
        log(
            logger,
            "IMPACT_CACHE_HIT",
            level=logging.INFO,
            analysis=str(cached.id),
            asset=asset.display_name,
            column=target_column,
        )
        return cached, True

    log(
        logger,
        "IMPACT_START",
        level=logging.INFO,
        asset=asset.display_name,
        column=target_column or "(all)",
        change_type=change_type,
    )

    assets = {str(a.id): a for a in db.query(DataAsset).all()}
    transformations = {str(t.id): t for t in db.query(Transformation).all()}
    edges = db.query(LineageEdge).all()
    edge_payload = [
        {
            "source_asset_id": str(edge.source_asset_id),
            "source_column": edge.source_column,
            "target_asset_id": str(edge.target_asset_id),
            "target_column": edge.target_column,
            "edge_kind": edge.edge_kind,
            "transformation_id": str(edge.transformation_id),
        }
        for edge in edges
    ]
    adjacency = build_adjacency(edge_payload)
    node_meta: dict[tuple[str, str], dict] = {}
    for edge in edge_payload:
        target = (edge["target_asset_id"], edge["target_column"])
        node_meta.setdefault(
            target,
            {"edge_kind": edge["edge_kind"], "via_transformation_id": edge["transformation_id"]},
        )

    # 起点：指定列，或资产的所有有出边的列
    if target_column:
        starts = [(str(target_asset_id), target_column)]
    else:
        starts = [
            source
            for source in adjacency.keys()
            if source[0] == str(target_asset_id)
        ]
        if not starts:
            starts = [(str(target_asset_id), column.get("name")) for column in asset.columns_json or []]

    depths: dict[tuple[str, str], int] = {}
    parents: dict[tuple[str, str], tuple[str, str] | None] = {}
    truncated = False
    for start in starts:
        if start not in adjacency:
            adjacency.setdefault(start, [])
        local_depths, local_truncated = reachable(adjacency, start, MAX_IMPACT_DEPTH)
        truncated = truncated or local_truncated
        for node, depth in local_depths.items():
            if node not in depths or depth < depths[node]:
                depths[node] = depth
        # 用 BFS 补父节点，构造传播路径
        if not parents:
            parents[start] = None
            queue = deque([start])
            seen = {start}
            while queue:
                current = queue.popleft()
                for neighbor in adjacency.get(current, []):
                    if neighbor in seen:
                        continue
                    seen.add(neighbor)
                    parents[neighbor] = current
                    queue.append(neighbor)

    if truncated:
        log(
            logger,
            "IMPACT_TRUNCATED",
            level=logging.WARNING,
            limit=MAX_IMPACT_DEPTH,
            affected=len(depths),
        )

    affected: list[dict] = []
    for (asset_key, column), depth in sorted(depths.items(), key=lambda item: item[1]):
        node_asset = assets.get(asset_key)
        if node_asset is None:
            continue
        meta = node_meta.get((asset_key, column), {})
        affected.append(
            {
                "asset_id": asset_key,
                "asset_name": node_asset.display_name,
                "asset_type": node_asset.asset_type,
                "column": column,
                "depth": depth,
                "edge_kind": meta.get("edge_kind", "direct"),
                "via_transformation_id": meta.get("via_transformation_id"),
                "severity": _severity_from_depth(depth).value,
            }
        )

    affected_assets = {node["asset_id"] for node in affected}
    min_depth = min((node["depth"] for node in affected), default=None)
    max_depth = max((node["depth"] for node in affected), default=0)
    cycles = find_cycles(adjacency)
    cycle_nodes = {node for cycle in cycles for node in cycle["nodes"]} if False else set()
    # 环是否命中本次可达集合
    cycle_node_pairs = {
        (entry["asset_id"], entry["column"]) for cycle in cycles for entry in cycle["nodes"]
    }
    hit_cycle = bool(cycle_node_pairs & set(depths.keys()))
    has_mv = any(
        assets.get(node["asset_id"]) is not None
        and assets[node["asset_id"]].asset_type == AssetType.materialized_view.value
        for node in affected
    )
    severity = grade_severity(
        min_depth=min_depth,
        change_type=change_type,
        has_materialized_view=has_mv,
        has_cycle=hit_cycle,
    )

    # 传播路径（每个受影响列一条最短路径）
    path_items: list[dict] = []
    for node in affected:
        key = (node["asset_id"], node["column"])
        chain: list[dict] = []
        cursor = key
        guard = 0
        while cursor is not None and guard < MAX_IMPACT_DEPTH + 2:
            guard += 1
            asset_obj = assets.get(cursor[0])
            chain.append(
                {
                    "asset_id": cursor[0],
                    "asset_name": asset_obj.display_name if asset_obj else cursor[0],
                    "column": cursor[1],
                }
            )
            cursor = parents.get(cursor)
        chain.reverse()
        path_items.append(
            {
                "target": {
                    "asset_id": node["asset_id"],
                    "asset_name": node["asset_name"],
                    "column": node["column"],
                },
                "depth": node["depth"],
                "path": chain,
            }
        )

    display_cycles = []
    for cycle in cycles:
        nodes = [
            {
                "asset_id": entry["asset_id"],
                "asset_name": assets[entry["asset_id"]].display_name
                if entry["asset_id"] in assets
                else entry["asset_id"],
                "column": entry["column"],
            }
            for entry in cycle["nodes"]
        ]
        display_cycles.append({"nodes": nodes, "sample_path": cycle["sample_path"]})

    checklist = _build_checklist(affected, assets, change_type)
    report_assets = affected_assets - {
        node["asset_id"]
        for node in affected
        if assets.get(node["asset_id"]) is not None
        and assets[node["asset_id"]].asset_type == AssetType.cte_result.value
    }

    report = {
        "target": {
            "asset_id": str(target_asset_id),
            "asset_name": asset.display_name,
            "column": target_column,
            "change_type": change_type,
        },
        "summary": {
            "severity": severity.value,
            "severity_label": {
                "low": "低",
                "medium": "中",
                "high": "高",
                "critical": "严重",
            }[severity.value],
            "affected_assets": len(affected_assets),
            "affected_columns": len(affected),
            "reports": len(report_assets),
            "min_depth": min_depth,
            "max_depth": max_depth,
            "truncated": truncated,
            "depth_limit": MAX_IMPACT_DEPTH,
        },
        "nodes": affected,
        "paths": path_items,
        "cycles": display_cycles,
        "cycle_hit": hit_cycle,
        "migration_checklist": checklist,
        "truncated": truncated,
        "excluded_from_checklist": sorted(
            {
                node["asset_name"]
                for node in affected
                if assets.get(node["asset_id"]) is not None
                and assets[node["asset_id"]].asset_type == AssetType.cte_result.value
            }
        ),
    }

    analysis = ImpactAnalysis(
        requested_by=user.id,
        change_type=change_type,
        target_asset_id=target_asset_id,
        target_column=target_column,
        severity=severity.value,
        affected_count=len(affected),
        report_json=report,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    log(
        logger,
        "IMPACT_GRADED",
        level=logging.INFO,
        severity=severity.value,
        affected=len(affected),
        reports=len(report_assets),
        depth=min_depth,
    )
    return analysis, False


def history(db: Session, limit: int = 20) -> list[dict]:
    assets = {str(a.id): a for a in db.query(DataAsset).all()}
    rows = db.query(ImpactAnalysis).order_by(ImpactAnalysis.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(row.id),
            "requested_by": str(row.requested_by),
            "change_type": row.change_type,
            "target_asset_id": str(row.target_asset_id),
            "target_asset_name": assets[row.target_asset_id].display_name
            if row.target_asset_id in assets
            else None,
            "target_column": row.target_column,
            "severity": row.severity,
            "affected_count": row.affected_count,
            "created_at": row.created_at.isoformat(),
            "summary": (row.report_json or {}).get("summary", {}),
        }
        for row in rows
    ]


def get_analysis(db: Session, analysis_id: uuid.UUID) -> ImpactAnalysis:
    row = db.get(ImpactAnalysis, analysis_id)
    if row is None:
        raise AppError(E_NOT_FOUND, "影响分析不存在", entity="impact_analysis", field="id")
    return row
