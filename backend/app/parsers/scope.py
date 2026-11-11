"""作用域栈：CTE / 子查询 / 派生表的注册与查找。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Ref:
    """一条列级来源引用（最终会落成 LineageEdge）。"""

    asset_id: str
    column: str
    kind: str = "direct"
    expression_text: str | None = None

    def copy(self, kind: str | None = None, expression_text: str | None = None) -> "Ref":
        return Ref(
            asset_id=self.asset_id,
            column=self.column,
            kind=kind or self.kind,
            expression_text=expression_text if expression_text is not None else self.expression_text,
        )


@dataclass
class SourceEntry:
    """作用域里的一个数据来源：真实表、CTE 或子查询。"""

    label: str
    asset_id: str | None
    columns: list[str] = field(default_factory=list)
    # 派生来源（CTE / 子查询）的列 → 已溯源到真实资产的引用
    lineage: dict[str, list[Ref]] = field(default_factory=dict)
    complete: bool = True
    missing: list[str] = field(default_factory=list)
    derived: bool = False
    source_asset: object | None = None  # AssetInfo（真实表时有值）

    def refs_for(self, column: str) -> list[Ref]:
        if self.derived:
            return list(self.lineage.get(column, []))
        if self.asset_id is None:
            return []
        return [Ref(asset_id=self.asset_id, column=column, kind="direct", expression_text=column)]


class Scope:
    """作用域：一个 SELECT 及其 FROM/JOIN/CTE 的可见来源集合。"""

    def __init__(self, parent: "Scope | None" = None):
        self.parent = parent
        self.entries: dict[str, SourceEntry] = {}

    def register(self, keys: list[str], entry: SourceEntry) -> None:
        for key in keys:
            if key:
                self.entries[key.lower()] = entry

    def lookup(self, key: str) -> SourceEntry | None:
        k = (key or "").lower().strip('"')
        if not k:
            return None
        entry = self.entries.get(k)
        if entry is not None:
            return entry
        # 允许用 schema.name / name 命中
        for registered, candidate in self.entries.items():
            if registered.endswith("." + k) or registered.split(".")[-1] == k:
                return candidate
        if self.parent is not None:
            return self.parent.lookup(k)
        return None

    def candidates_for_column(self, column: str) -> list[tuple[SourceEntry, list[Ref]]]:
        found: list[tuple[SourceEntry, list[Ref]]] = []
        seen: set[int] = set()
        for entry in self.entries.values():
            if id(entry) in seen:
                continue
            seen.add(id(entry))
            if column in entry.columns:
                found.append((entry, entry.refs_for(column)))
        if not found and self.parent is not None:
            return self.parent.candidates_for_column(column)
        return found

    def unique_entries(self) -> list[SourceEntry]:
        seen: set[int] = set()
        result: list[SourceEntry] = []
        for entry in self.entries.values():
            if id(entry) not in seen:
                seen.add(id(entry))
                result.append(entry)
        return result
