"""解析引擎：SQL 语句 → 列级引用图（不依赖数据库）。

对外入口：`parse_sql(sql_text, dialect, output_asset, input_assets)`。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from app.parsers.context import AssetInfo, ParseContext
from app.parsers.projection import ProjectionBuilder, classify_expr
from app.parsers.scope import Ref, Scope, SourceEntry
from app.parsers.star import expand_star  # noqa: F401  （star 由 projection 调用，此处保留导出）


@dataclass
class ParseResult:
    status: str
    columns: dict[str, list[Ref]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    parse_error: str | None = None
    error_line: int | None = None
    error_column: int | None = None
    star_expanded: bool = False
    edge_count: int = 0

    def to_report(self) -> dict:
        return {
            "status": self.status,
            "warnings": self.warnings,
            "unresolved": self.unresolved,
            "star_expanded": self.star_expanded,
            "parse_error": self.parse_error,
            "error_line": self.error_line,
            "error_column": self.error_column,
            "edge_count": self.edge_count,
            "columns": [
                {"target_column": target, "sources": [f"{r.asset_id}:{r.column}" for r in refs]}
                for target, refs in self.columns.items()
            ],
        }


def extract_select(stmt: exp.Expression | None) -> exp.Select | None:
    """从语句里取出 SELECT（支持 CREATE ... AS SELECT / INSERT ... SELECT）。"""
    if stmt is None:
        return None
    if isinstance(stmt, exp.Select):
        return stmt
    if isinstance(stmt, exp.Subquery):
        return extract_select(stmt.this)
    if isinstance(stmt, exp.Create):
        return extract_select(stmt.expression)
    if isinstance(stmt, exp.Insert):
        return extract_select(stmt.expression)
    if isinstance(stmt, exp.Union):
        return None
    return None


def parse_sql(
    sql_text: str,
    dialect: str,
    output_asset: AssetInfo,
    input_assets: list[AssetInfo],
) -> ParseResult:
    ctx = ParseContext(dialect=dialect, output_asset=output_asset, input_assets=input_assets)
    try:
        statements = sqlglot.parse(sql_text, dialect=dialect)
    except sqlglot.errors.ParseError as exc:
        line, column = _error_position(exc)
        return ParseResult(
            status="failed",
            parse_error=str(exc),
            error_line=line,
            error_column=column,
            warnings=["sqlglot 解析失败，未产出任何血缘边"],
        )
    except Exception as exc:  # pragma: no cover - 非预期异常
        return ParseResult(status="failed", parse_error=f"{type(exc).__name__}: {exc}")

    select = None
    for stmt in statements or []:
        candidate = extract_select(stmt)
        if candidate is not None:
            select = candidate

    if select is None:
        return ParseResult(
            status="failed",
            parse_error="未在 SQL 中找到可解析的 SELECT 语句（支持 SELECT / INSERT ... SELECT / CREATE ... AS SELECT）",
        )

    try:
        columns = process_select(select, Scope(), ctx)
    except sqlglot.errors.ParseError as exc:
        line, column = _error_position(exc)
        return ParseResult(
            status="failed", parse_error=str(exc), error_line=line, error_column=column
        )
    except Exception as exc:  # pragma: no cover - 解析器内部保护
        return ParseResult(status="failed", parse_error=f"{type(exc).__name__}: {exc}")

    status = "partial" if ctx.partial else "parsed"
    if status == "parsed" and not columns:
        ctx.mark_partial("empty_projection", detail="未能推导任何输出列", warning="未能推导任何输出列")
        status = "partial"
    edge_count = sum(len(refs) for refs in columns.values())
    return ParseResult(
        status=status,
        columns=columns,
        warnings=ctx.warnings,
        unresolved=[issue.to_dict() for issue in ctx.unresolved],
        star_expanded=ctx.star_expanded,
        edge_count=edge_count,
    )


def _error_position(exc: sqlglot.errors.ParseError) -> tuple[int | None, int | None]:
    try:
        errors = getattr(exc, "errors", None) or []
        if errors:
            line = errors[0].get("line")
            col = errors[0].get("col")
            return line, col
    except Exception:
        pass
    return None, None


def process_select(select: exp.Select, outer_scope: Scope, ctx: ParseContext) -> dict[str, list[Ref]]:
    """处理一个 SELECT：先注册 CTE/子查询作用域，再展开投影。"""
    if isinstance(select, exp.Union):
        ctx.mark_partial(
            "union_not_supported",
            detail="UNION / EXCEPT / INTERSECT 暂未做列级展开",
            warning="UNION 语句暂未做列级展开，结果记为 partial",
        )
        select = select.this if isinstance(select.this, exp.Select) else None
        if select is None:
            return {}

    cte_scope = Scope(parent=outer_scope)
    builder = ProjectionBuilder(ctx)

    # 1) CTE：按顺序注册到 cte_scope，后一个 CTE 可以引用前面的 CTE
    with_clause = select.args.get("with")
    if with_clause is not None:
        for cte in with_clause.expressions:
            if not isinstance(cte, exp.CTE):
                continue
            inner = extract_select(cte.this)
            if inner is None:
                ctx.mark_partial(
                    "cte_not_select",
                    detail=f"CTE {cte.alias} 不是 SELECT",
                    warning=f"CTE {cte.alias} 不是 SELECT，跳过",
                )
                continue
            inner_columns = process_select(inner, cte_scope, ctx)
            entry = SourceEntry(
                label=cte.alias,
                asset_id=None,
                columns=list(inner_columns.keys()),
                lineage=inner_columns,
                complete=True,
                derived=True,
            )
            cte_scope.register([cte.alias], entry)

    # 2) FROM / JOIN 注册到本层作用域（避免与 CTE 名混淆）
    scope = Scope(parent=cte_scope)
    from_clause = select.args.get("from")
    sources: list[tuple[exp.Expression, str]] = []
    if from_clause is not None and from_clause.this is not None:
        sources.append((from_clause.this, "from"))
    for join in select.args.get("joins") or []:
        if join.this is not None:
            sources.append((join.this, "join"))

    for source, _kind in sources:
        entry = _register_source(source, scope, ctx)
        if entry is not None:
            keys = _source_keys(source)
            scope.register(keys, entry)

    # 3) JOIN ON 中的列对（后面用来把 direct 边细化成 join_key）
    join_pairs: list[tuple[Ref, Ref]] = []
    for join in select.args.get("joins") or []:
        on_expr = join.args.get("on")
        if on_expr is None:
            continue
        for node in on_expr.walk():
            if isinstance(node, exp.EQ):
                left = _column_ref(builder, node.this, scope, "join_key")
                right = _column_ref(builder, node.expression, scope, "join_key")
                if left and right:
                    join_pairs.append((left, right))

    # 4) 投影展开
    outputs = builder.build(select, scope)

    # 5) join_key 细化：投影里同源同列的 direct 边升级为 join_key
    if join_pairs:
        join_keys = {(ref.asset_id, ref.column) for pair in join_pairs for ref in pair}
        for target, refs in outputs.items():
            for index, ref in enumerate(refs):
                if ref.kind == "direct" and (ref.asset_id, ref.column) in join_keys:
                    outputs[target][index] = ref.copy(kind="join_key")
    return outputs


def _source_keys(source: exp.Expression) -> list[str]:
    keys: list[str] = []
    alias = source.alias_or_name
    if alias:
        keys.append(alias)
    if isinstance(source, exp.Table):
        if source.name:
            keys.append(source.name)
        if source.db and source.name:
            keys.append(f"{source.db}.{source.name}")
        if source.catalog and source.db and source.name:
            keys.append(f"{source.catalog}.{source.db}.{source.name}")
    return keys


def _register_source(source: exp.Expression, scope: Scope, ctx: ParseContext) -> SourceEntry | None:
    if isinstance(source, exp.Table):
        table_name = source.name
        qualified = f"{source.db}.{table_name}" if source.db else table_name
        cte_entry = scope.lookup(table_name) or scope.parent.lookup(table_name) if scope.parent else scope.lookup(table_name)
        if cte_entry is not None and cte_entry.derived:
            return cte_entry
        asset = ctx.find_asset(qualified) or ctx.find_asset(table_name)
        if asset is None:
            ctx.mark_partial(
                "unknown_input_asset",
                detail=f"FROM 中的表 {qualified} 不在该转换的输入资产清单内",
                warning=f"表 {qualified} 不在输入资产清单内，无法溯源",
            )
            return SourceEntry(label=qualified, asset_id=None, columns=[], complete=False, missing=["*"])
        entry = SourceEntry(
            label=asset.display_name,
            asset_id=asset.id,
            columns=asset.registered_columns,
            complete=asset.columns_complete,
            missing=asset.missing_columns,
            derived=False,
            source_asset=asset,
        )
        if not asset.columns_complete:
            ctx.warn(
                f"输入资产 {asset.display_name} 列清单不完整"
                + (f"，缺少 {', '.join(asset.missing_columns)}" if asset.missing_columns else "")
            )
        return entry

    if isinstance(source, exp.Subquery):
        inner = extract_select(source.this)
        if inner is None:
            ctx.mark_partial(
                "subquery_not_select",
                detail="派生表不是 SELECT",
                warning="派生表不是 SELECT，跳过",
            )
            return None
        inner_columns = process_select(inner, scope, ctx)
        alias = source.alias or "subquery"
        return SourceEntry(
            label=alias,
            asset_id=None,
            columns=list(inner_columns.keys()),
            lineage=inner_columns,
            complete=True,
            derived=True,
        )

    if isinstance(source, exp.Lateral):
        return _register_source(source.this, scope, ctx)

    if isinstance(source, exp.Values):
        alias = source.alias or "values"
        return SourceEntry(label=alias, asset_id=None, columns=[], complete=True, derived=True)

    ctx.warn(f"暂不支持的 FROM 源类型：{type(source).__name__}")
    return None


def _column_ref(
    builder: ProjectionBuilder, node: exp.Expression, scope: Scope, expression_text: str
) -> Ref | None:
    if isinstance(node, exp.Paren):
        node = node.this
    if not isinstance(node, exp.Column):
        return None
    refs = builder.resolve_column(node, scope, expression_text)
    return refs[0] if refs else None


def classify_projection(expr: exp.Expression) -> str:
    return classify_expr(expr)
