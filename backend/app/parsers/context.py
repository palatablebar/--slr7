"""解析上下文：输入资产列清单、方言、告警与 partial 收集。

本模块不依赖数据库，纯数据结构，worker 与 backend 共用。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AssetColumn:
    name: str
    data_type: str | None = None
    nullable: bool | None = None
    ordinal: int | None = None
    description: str | None = None


@dataclass
class AssetInfo:
    """参与一次解析的资产视图（输入或输出）。"""

    id: str
    database_name: str
    schema_name: str
    name: str
    columns: list[AssetColumn] = field(default_factory=list)
    # 其它转换已经产出、但 columns_json 未登记的列（用于判定 SELECT * 不可展开）
    produced_columns: set[str] = field(default_factory=set)

    @property
    def display_name(self) -> str:
        return f"{self.schema_name}.{self.name}"

    @property
    def full_name(self) -> str:
        return f"{self.database_name}.{self.schema_name}.{self.name}"

    @property
    def registered_columns(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def missing_columns(self) -> list[str]:
        registered = set(self.registered_columns)
        return sorted(self.produced_columns - registered)

    @property
    def columns_complete(self) -> bool:
        return bool(self.columns) and not self.missing_columns

    def keys(self) -> list[str]:
        keys = {self.name.lower(), self.display_name.lower(), self.full_name.lower()}
        return [k for k in keys if k]


@dataclass
class UnresolvedIssue:
    reason: str
    column: str | None = None
    asset_id: str | None = None
    asset_name: str | None = None
    missing: list[str] = field(default_factory=list)
    detail: str | None = None

    def to_dict(self) -> dict:
        return {
            "reason": self.reason,
            "column": self.column,
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "missing": self.missing,
            "detail": self.detail,
        }


@dataclass
class ParseContext:
    dialect: str
    output_asset: AssetInfo
    input_assets: list[AssetInfo]
    warnings: list[str] = field(default_factory=list)
    unresolved: list[UnresolvedIssue] = field(default_factory=list)
    star_expanded: bool = False
    partial: bool = False

    def find_asset(self, table_key: str) -> AssetInfo | None:
        key = (table_key or "").lower().strip('"')
        if not key:
            return None
        # 优先完整名，其次 schema.name，最后裸表名
        for asset in self.input_assets:
            if key == asset.full_name.lower():
                return asset
        for asset in self.input_assets:
            if key == asset.display_name.lower():
                return asset
        for asset in self.input_assets:
            if key == asset.name.lower():
                return asset
        return None

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def mark_partial(
        self,
        reason: str,
        *,
        column: str | None = None,
        asset: AssetInfo | None = None,
        missing: list[str] | None = None,
        detail: str | None = None,
        warning: str | None = None,
    ) -> UnresolvedIssue:
        self.partial = True
        issue = UnresolvedIssue(
            reason=reason,
            column=column,
            asset_id=asset.id if asset else None,
            asset_name=asset.display_name if asset else None,
            missing=list(missing or []),
            detail=detail,
        )
        if not any(
            u.reason == issue.reason and u.column == issue.column and u.asset_id == issue.asset_id
            for u in self.unresolved
        ):
            self.unresolved.append(issue)
        if warning:
            self.warn(warning)
        return issue
