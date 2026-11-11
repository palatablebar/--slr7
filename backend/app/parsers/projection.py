"""投影表达式 → 列级边（含聚合/派生分类）。"""
from __future__ import annotations

from sqlglot import exp

from app.constants.edge import EDGE_KIND_PRIORITY, EdgeKind
from app.parsers.context import ParseContext
from app.parsers.scope import Ref, Scope
from app.parsers.star import expand_star


def _priority(kind: str) -> int:
    try:
        return EDGE_KIND_PRIORITY[EdgeKind(kind)]
    except ValueError:
        return 0


def classify_expr(expr: exp.Expression) -> str:
    """表达式分类：aggregate > derived > direct。"""
    has_aggregate = False
    has_derived = False
    for node in expr.walk():
        if isinstance(node, exp.AggFunc):
            has_aggregate = True
        elif isinstance(
            node,
            (
                exp.Cast,
                exp.TryCast,
                exp.Concat,
                exp.DPipe,
                exp.Case,
                exp.If,
                exp.Coalesce,
                exp.Binary,
                exp.Paren,
                exp.Extract,
                exp.Round,
                exp.Anonymous,
                exp.Window,
            ),
        ):
            # 普通函数/算术/拼接/CASE 都算表达式派生
            if not isinstance(node, exp.Column):
                has_derived = True
    if has_aggregate:
        return EdgeKind.aggregate.value
    if has_derived:
        return EdgeKind.derived.value
    return EdgeKind.direct.value


def output_name(expr: exp.Expression, index: int) -> str:
    if isinstance(expr, exp.Alias):
        return expr.alias
    if isinstance(expr, exp.Column):
        return expr.name
    if isinstance(expr, exp.Star):
        return "*"
    name = expr.alias_or_name
    return name or f"col_{index + 1}"


def merge_ref(store: dict[tuple[str, str], Ref], ref: Ref, kind: str | None = None) -> None:
    candidate = ref.copy(kind=kind) if kind else ref
    key = (candidate.asset_id, candidate.column)
    existing = store.get(key)
    if existing is None or _priority(candidate.kind) > _priority(existing.kind):
        store[key] = candidate


class ProjectionBuilder:
    """把一个 SELECT 的投影列展开成 target_column → [Ref]。"""

    def __init__(self, ctx: ParseContext):
        self.ctx = ctx

    # ---------- 列解析 ----------
    def resolve_column(self, column: exp.Column, scope: Scope, expression_text: str) -> list[Ref]:
        table_key = column.table
        column_name = column.name
        if table_key:
            entry = scope.lookup(table_key)
            if entry is None:
                self.ctx.mark_partial(
                    "unresolved_table",
                    column=column_name,
                    detail=f"列 {column_name} 的表限定 {table_key} 未在当前作用域中找到",
                    warning=f"表限定 {table_key} 未解析，列 {column_name} 记为 partial",
                )
                return []
            if entry.derived:
                refs = entry.refs_for(column_name)
                if not refs:
                    self.ctx.mark_partial(
                        "unresolved_column",
                        column=column_name,
                        detail=f"派生表 {entry.label} 中没有列 {column_name}",
                        warning=f"派生表 {entry.label} 缺少列 {column_name}",
                    )
                return [r.copy(expression_text=r.expression_text or expression_text) for r in refs]
            if entry.asset_id is None:
                return []
            return [Ref(entry.asset_id, column_name, "direct", expression_text)]

        candidates = scope.candidates_for_column(column_name)
        if len(candidates) == 1:
            entry, refs = candidates[0]
            return [r.copy(expression_text=r.expression_text or expression_text) for r in refs]
        if len(candidates) > 1:
            entry, refs = candidates[0]
            others = ", ".join(c[0].label for c in candidates[1:])
            self.ctx.mark_partial(
                "ambiguous_column",
                column=column_name,
                asset=entry.source_asset if hasattr(entry, "source_asset") else None,
                detail=f"裸列 {column_name} 命中多个来源（{entry.label} / {others}），取最内层 {entry.label}",
                warning=f"裸列 {column_name} 命中多个来源，按最内层作用域解析",
            )
            return [r.copy(expression_text=r.expression_text or expression_text) for r in refs]
        self.ctx.mark_partial(
            "unresolved_column",
            column=column_name,
            detail=f"裸列 {column_name} 无法匹配任何输入资产/派生表的列",
            warning=f"列 {column_name} 无法溯源到输入资产",
        )
        return []

    def collect_refs(self, expr: exp.Expression, scope: Scope) -> dict[tuple[str, str], Ref]:
        expression_text = _safe_sql(expr)
        collected: dict[tuple[str, str], Ref] = {}
        for node in expr.walk():
            if isinstance(node, exp.Star):
                continue
            if isinstance(node, exp.Column) and isinstance(node.this, exp.Star):
                # t.* 形式
                for ref in expand_star(node, scope, self.ctx, qualified=node.table):
                    merge_ref(collected, ref)
                continue
            if isinstance(node, exp.Column):
                for ref in self.resolve_column(node, scope, expression_text):
                    merge_ref(collected, ref)
        kind = classify_expr(expr)
        if kind != EdgeKind.direct.value:
            for key, ref in list(collected.items()):
                if _priority(kind) >= _priority(ref.kind):
                    collected[key] = ref.copy(kind=kind, expression_text=expression_text)
        elif collected:
            for key, ref in list(collected.items()):
                collected[key] = ref.copy(expression_text=expression_text)
        return collected

    # ---------- 构建 ----------
    def build(self, select: exp.Select, scope: Scope) -> dict[str, list[Ref]]:
        raw: dict[str, dict[tuple[str, str], Ref]] = {}
        for index, projection in enumerate(select.expressions):
            inner = projection.this if isinstance(projection, exp.Alias) else projection
            if isinstance(inner, exp.Star) or (
                isinstance(inner, exp.Column) and isinstance(inner.this, exp.Star)
            ):
                qualified = inner.table if isinstance(inner, exp.Column) else ""
                star_map = expand_star(inner, scope, self.ctx, qualified=qualified)
                for target_column, refs in star_map.items():
                    store = raw.setdefault(target_column, {})
                    for ref in refs:
                        merge_ref(store, ref)
                self.ctx.star_expanded = True
                continue
            target_column = output_name(projection, index)
            refs_map = self.collect_refs(inner, scope)
            store = raw.setdefault(target_column, {})
            for ref in refs_map.values():
                merge_ref(store, ref)
        return {target: list(store.values()) for target, store in raw.items()}


def _safe_sql(expr: exp.Expression) -> str:
    try:
        return expr.sql(pretty=False)
    except Exception:
        return ""
