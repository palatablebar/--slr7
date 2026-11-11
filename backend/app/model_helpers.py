"""模型 → 解析器数据结构的适配层（避免 service 与 parser 互相依赖）。"""
from __future__ import annotations

from app.models.data_asset import DataAsset
from app.parsers.context import AssetColumn, AssetInfo


def asset_info_from_model(asset: DataAsset, produced_columns: set[str] | None = None) -> AssetInfo:
    columns = [
        AssetColumn(
            name=col.get("name", ""),
            data_type=col.get("data_type"),
            nullable=col.get("nullable"),
            ordinal=col.get("ordinal"),
            description=col.get("description"),
        )
        for col in (asset.columns_json or [])
        if col.get("name")
    ]
    return AssetInfo(
        id=str(asset.id),
        database_name=asset.database_name,
        schema_name=asset.schema_name,
        name=asset.name,
        columns=columns,
        produced_columns=set(produced_columns or set()),
    )
