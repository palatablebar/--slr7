"""SELECT * 展开与 partial 判定。"""
from __future__ import annotations

from sqlglot import exp

from app.parsers.context import ParseContext
from app.parsers.scope import Ref, Scope


def expand_star(
    node: exp.Expression,
    scope: Scope,
    ctx: ParseContext,
    qualified: str = "",
) -> dict[str, list[Ref]]:
    """把 `*` / `t.*` 展开为 target_column → refs。

    来源资产 columns_json 完整时逐列展开为 direct 边；
    为空 / 缺少（由上游转换产出但未登记的）列时置 partial，并记录未展开的列。
    """
    ctx.star_expanded = True
    entries = scope.unique_entries()
    if qualified:
        entry = scope.lookup(qualified)
        if entry is None:
            ctx.mark_partial(
                "star_unresolved_table",
                column="*",
                detail=f"t.* 的限定表 {qualified} 未在当前作用域找到",
                warning=f"t.* 的限定表 {qualified} 未解析",
            )
            return {}
        entries = [entry]

    result: dict[str, list[Ref]] = {}
    for entry in entries:
        if not entry.columns:
            missing = list(entry.missing) or ["*"]
            ctx.mark_partial(
                "star_unexpanded",
                column="*",
                asset=entry.source_asset,
                missing=missing,
                detail=f"{entry.label} 的列清单为空，无法展开 *",
                warning=f"{entry.label} 列清单为空，SELECT * 无法展开",
            )
            continue
        for column in entry.columns:
            refs = entry.refs_for(column)
            if entry.asset_id is None and not refs:
                continue
            result.setdefault(column, []).extend(refs)
        if not entry.complete:
            ctx.mark_partial(
                "star_unexpanded",
                column="*",
                asset=entry.source_asset,
                missing=list(entry.missing) or ["*"],
                detail=(
                    f"{entry.label} 的 columns_json 缺少列 "
                    f"{', '.join(entry.missing) if entry.missing else '(未知)'}，"
                    "已展开已登记列，未登记列无法展开"
                ),
                warning=(
                    f"{entry.label} 列清单缺列 "
                    f"{', '.join(entry.missing) if entry.missing else '(未知)'}，SELECT * 记为 partial"
                ),
            )
    return result
