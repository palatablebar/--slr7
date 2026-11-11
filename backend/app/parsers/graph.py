"""有向图构建、Tarjan 环检测、可达性 BFS。"""
from __future__ import annotations

from collections import deque


def build_adjacency(edges: list[dict]) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """edges: [{source_asset_id, source_column, target_asset_id, target_column, edge_kind}]

    返回 source_node → [target_node] 的邻接表，节点为 (asset_id, column)。
    """
    adjacency: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for edge in edges:
        source = (str(edge["source_asset_id"]), edge["source_column"])
        target = (str(edge["target_asset_id"]), edge["target_column"])
        adjacency.setdefault(source, [])
        if target not in adjacency[source]:
            adjacency[source].append(target)
        adjacency.setdefault(target, [])
    return adjacency


def tarjan_scc(adjacency: dict[tuple[str, str], list[tuple[str, str]]]) -> list[list[tuple[str, str]]]:
    """Tarjan 强连通分量；返回尺寸 > 1 或带自环的分量。"""
    index_counter = [0]
    stack: list[tuple[str, str]] = []
    lowlink: dict[tuple[str, str], int] = {}
    index: dict[tuple[str, str], int] = {}
    on_stack: dict[tuple[str, str], bool] = {}
    components: list[list[tuple[str, str]]] = []

    def strongconnect(node: tuple[str, str]) -> None:
        index[node] = index_counter[0]
        lowlink[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True

        for neighbor in adjacency.get(node, []):
            if neighbor not in index:
                strongconnect(neighbor)
                lowlink[node] = min(lowlink[node], lowlink[neighbor])
            elif on_stack.get(neighbor):
                lowlink[node] = min(lowlink[node], index[neighbor])

        if lowlink[node] == index[node]:
            component: list[tuple[str, str]] = []
            while True:
                member = stack.pop()
                on_stack[member] = False
                component.append(member)
                if member == node:
                    break
            self_loop = len(component) == 1 and node in adjacency.get(node, [])
            if len(component) > 1 or self_loop:
                components.append(component)

    for node in list(adjacency.keys()):
        if node not in index:
            strongconnect(node)
    return components


def find_cycles(adjacency: dict[tuple[str, str], list[tuple[str, str]]]) -> list[dict]:
    """返回环描述：{nodes, sample_path}。"""
    cycles: list[dict] = []
    for component in tarjan_scc(adjacency):
        members = set(component)
        start = component[0]
        path = _shortest_cycle_path(adjacency, start, members)
        cycles.append(
            {
                "nodes": [{"asset_id": a, "column": c} for a, c in component],
                "sample_path": [{"asset_id": a, "column": c} for a, c in (path or component)],
            }
        )
    return cycles


def _shortest_cycle_path(
    adjacency: dict[tuple[str, str], list[tuple[str, str]]],
    start: tuple[str, str],
    members: set[tuple[str, str]],
) -> list[tuple[str, str]] | None:
    """BFS 找回环路径：start → ... → start。"""
    queue: deque[list[tuple[str, str]]] = deque([[start]])
    seen: set[tuple[str, str]] = {start}
    while queue:
        path = queue.popleft()
        node = path[-1]
        for neighbor in adjacency.get(node, []):
            if neighbor == start:
                return path + [start]
            if neighbor in members and neighbor not in seen:
                seen.add(neighbor)
                queue.append(path + [neighbor])
    return None


def reachable(
    adjacency: dict[tuple[str, str], list[tuple[str, str]]],
    start: tuple[str, str],
    max_depth: int = 12,
) -> tuple[dict[tuple[str, str], int], bool]:
    """BFS 求下游可达集合与最小深度；返回 (node → depth, truncated)。"""
    depths: dict[tuple[str, str], int] = {}
    truncated = False
    queue: deque[tuple[tuple[str, str], int]] = deque([(start, 0)])
    visited = {start}
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            if adjacency.get(node):
                truncated = True
            continue
        for neighbor in adjacency.get(node, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            depths[neighbor] = depth + 1
            queue.append((neighbor, depth + 1))
    return depths, truncated


def paths_to(
    adjacency: dict[tuple[str, str], list[tuple[str, str]]],
    start: tuple[str, str],
    target: tuple[str, str],
    max_nodes: int = 200,
) -> list[list[tuple[str, str]]]:
    """用 DFS 找出少量示例路径（用于报告展示）。"""
    results: list[list[tuple[str, str]]] = []

    def dfs(node: tuple[str, str], path: list[tuple[str, str]], seen: set[tuple[str, str]]) -> None:
        if len(results) >= max_nodes:
            return
        if node == target:
            results.append(list(path))
            return
        for neighbor in adjacency.get(node, []):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            path.append(neighbor)
            dfs(neighbor, path, seen)
            path.pop()
            seen.discard(neighbor)

    dfs(start, [start], {start})
    return results
