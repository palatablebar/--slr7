"""资产枚举与展示常量。"""
from enum import Enum


class AssetType(str, Enum):
    table = "table"
    view = "view"
    materialized_view = "materialized_view"
    cte_result = "cte_result"


class AssetStatus(str, Enum):
    active = "active"
    deprecated = "deprecated"
    draft = "draft"


ASSET_TYPE_LABELS = {
    AssetType.table: "表",
    AssetType.view: "视图",
    AssetType.materialized_view: "物化视图",
    AssetType.cte_result: "CTE 结果",
}

ASSET_STATUS_LABELS = {
    AssetStatus.active: "启用",
    AssetStatus.deprecated: "废弃",
    AssetStatus.draft: "草稿",
}

REPORT_EXCLUDED_ASSET_TYPES = {AssetType.cte_result}
