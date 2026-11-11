"""幂等演示数据 seed。

幂等键：
- 资产 (database_name, schema_name, name)
- 转换 name
- 血缘边 (transformation_id, source_column, target_column)（由 parse_service 先删后插保证）
- 历史结构变更事件 (asset_id, column_name, change_type, old_type, new_type)
- 历史影响分析（同参数已存在则不重算、不改写）

血缘边全部由 app/services/parse_service.py 真实解析生成，脚本内不手写任何边。
"""
from __future__ import annotations

import logging
import sys
import uuid

from app.config.database import SessionLocal
from app.constants import log_templates
from app.constants.change import ChangeType
from app.constants.roles import Role
from app.models.data_asset import DataAsset
from app.models.impact_analysis import ImpactAnalysis
from app.models.lineage_edge import LineageEdge
from app.models.schema_change_event import SchemaChangeEvent
from app.models.transformation import Transformation
from app.models.user import User
from app.services import asset_service, impact_service, parse_service, quota_service
from app.utils.logger import log
from app.utils.password import hash_password

logger = logging.getLogger("datatrace.seed")

DEMO_PASSWORD = "Demo@2026"

USERS = [
    {
        "email": "admin@datatrace.local",
        "display_name": "沈砚",
        "role": Role.admin.value,
    },
    {
        "email": "analyst@datatrace.local",
        "display_name": "周航",
        "role": Role.analyst.value,
    },
    {
        "email": "viewer@datatrace.local",
        "display_name": "林岚",
        "role": Role.viewer.value,
    },
]

DATABASE = "lanzo_dw"

ASSETS = [
    {
        "name": "orders",
        "schema_name": "ods",
        "asset_type": "table",
        "description": "交易订单原始表（ingest 自订单中心）",
        "columns": [
            {"name": "order_id", "data_type": "bigint", "nullable": False, "description": "订单号"},
            {"name": "user_id", "data_type": "bigint", "nullable": False, "description": "用户 ID"},
            {"name": "amount", "data_type": "decimal(18,2)", "nullable": False, "description": "订单金额"},
            {"name": "channel", "data_type": "varchar(32)", "nullable": True, "description": "渠道"},
            {"name": "region", "data_type": "varchar(32)", "nullable": True, "description": "大区"},
        ],
    },
    {
        "name": "order_detail",
        "schema_name": "dwd",
        "asset_type": "table",
        "description": "订单明细宽表（pay_method 由上游产出但本资产漏登记，用于演示 SELECT * partial）",
        "columns": [
            {"name": "order_id", "data_type": "bigint", "nullable": False, "description": "订单号"},
            {"name": "user_id", "data_type": "bigint", "nullable": False, "description": "用户 ID"},
            {"name": "pay_amount", "data_type": "decimal(18,2)", "nullable": False, "description": "实付金额"},
            {"name": "channel_region", "data_type": "varchar(64)", "nullable": True, "description": "渠道-大区"},
        ],
    },
    {
        "name": "user_gmv",
        "schema_name": "dws",
        "asset_type": "table",
        "description": "用户粒度 GMV 汇总",
        "columns": [
            {"name": "user_id", "data_type": "bigint", "nullable": False, "description": "用户 ID"},
            {"name": "gmv_amount", "data_type": "decimal(18,2)", "nullable": True, "description": "GMV 汇总"},
            {"name": "pay_cnt", "data_type": "bigint", "nullable": True, "description": "支付笔数"},
        ],
    },
    {
        "name": "gmv_daily",
        "schema_name": "ads",
        "asset_type": "table",
        "description": "GMV 日报（报表用）",
        "columns": [
            {"name": "user_id", "data_type": "bigint", "nullable": True, "description": "用户 ID"},
            {"name": "gmv", "data_type": "decimal(18,2)", "nullable": True, "description": "GMV"},
            {"name": "peak_gmv", "data_type": "decimal(18,2)", "nullable": True, "description": "GMV 峰值"},
            {"name": "region", "data_type": "varchar(32)", "nullable": True, "description": "大区"},
            {"name": "order_cnt", "data_type": "bigint", "nullable": True, "description": "订单数"},
        ],
    },
    {
        "name": "cte_result",
        "schema_name": "dwd",
        "asset_type": "cte_result",
        "description": "CTE / 临时汇总结果落地表（计入影响面，但不进迁移清单）",
        "columns": [
            {"name": "order_id", "data_type": "bigint", "nullable": True, "description": "订单号"},
            {"name": "user_id", "data_type": "bigint", "nullable": True, "description": "用户 ID"},
            {"name": "pay_amount", "data_type": "decimal(18,2)", "nullable": True, "description": "实付金额"},
            {"name": "channel_region", "data_type": "varchar(64)", "nullable": True, "description": "渠道-大区"},
            {"name": "region", "data_type": "varchar(32)", "nullable": True, "description": "大区"},
        ],
    },
]

TRANSFORMATIONS = [
    {
        "name": "t01_ods_orders_to_dwd_order_detail",
        "owner": "analyst",
        "inputs": ["ods.orders"],
        "output": "dwd.order_detail",
        "dialect": "postgres",
        "sql": """-- 基础投影 + CAST / CONCAT 表达式派生
SELECT o.order_id AS order_id,
       o.user_id  AS user_id,
       CAST(o.amount AS decimal(18,2)) AS pay_amount,
       CONCAT(o.channel, '-', o.region) AS channel_region,
       CAST(o.user_id % 10 AS int) AS pay_method
FROM ods.orders AS o
""",
    },
    {
        "name": "t02_dwd_to_dws_user_gmv",
        "owner": "analyst",
        "inputs": ["dwd.order_detail"],
        "output": "dws.user_gmv",
        "dialect": "postgres",
        "sql": """-- 聚合：SUM / COUNT 均归为 aggregate 边
SELECT user_id,
       SUM(pay_amount)  AS gmv_amount,
       COUNT(pay_amount) AS pay_cnt
FROM dwd.order_detail
GROUP BY user_id
""",
    },
    {
        "name": "t03_dws_to_ads_gmv_daily",
        "owner": "analyst",
        "inputs": ["dws.user_gmv"],
        "output": "ads.gmv_daily",
        "dialect": "postgres",
        "sql": """-- 子查询（派生表） + 聚合
SELECT g.user_id,
       SUM(g.gmv_amount) AS gmv,
       MAX(g.gmv_amount) AS peak_gmv
FROM (SELECT user_id, gmv_amount FROM dws.user_gmv) AS g
GROUP BY g.user_id
""",
    },
    {
        "name": "t04_region_rollup_with_cte",
        "owner": "admin",
        "inputs": ["ods.orders"],
        "output": "ads.gmv_daily",
        "dialect": "postgres",
        "sql": """-- 两层 CTE：base -> per_region
WITH base AS (
    SELECT order_id, region
    FROM ods.orders
), per_region AS (
    SELECT region, COUNT(*) AS order_cnt
    FROM base
    GROUP BY region
)
SELECT region, order_cnt
FROM per_region
""",
    },
    {
        "name": "t05_order_detail_orders_join",
        "owner": "analyst",
        "inputs": ["dwd.order_detail", "ods.orders"],
        "output": "dwd.cte_result",
        "dialect": "postgres",
        "sql": """-- 多输入 JOIN：ON 条件中的列对产出 join_key 边
SELECT d.order_id AS order_id,
       o.region   AS region
FROM dwd.order_detail AS d
JOIN ods.orders AS o
  ON d.order_id = o.order_id
""",
    },
    {
        "name": "t06_star_partial_from_order_detail",
        "owner": "admin",
        "inputs": ["dwd.order_detail"],
        "output": "dwd.cte_result",
        "dialect": "postgres",
        "sql": """-- SELECT * 无法完全展开：上游 dwd.order_detail 少登记了 pay_method
SELECT *
FROM dwd.order_detail
""",
    },
]


def _get_or_create_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for spec in USERS:
        user = db.query(User).filter(User.email == spec["email"]).first()
        if user is None:
            user = User(
                email=spec["email"],
                display_name=spec["display_name"],
                password_hash=hash_password(DEMO_PASSWORD),
                role=spec["role"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        users[spec["role"]] = user
        quota_service.get_or_create(db, user)
    return users


def _get_or_create_assets(db, admin: User) -> dict[str, DataAsset]:
    index: dict[str, DataAsset] = {}
    for spec in ASSETS:
        asset = (
            db.query(DataAsset)
            .filter(
                DataAsset.database_name == DATABASE,
                DataAsset.schema_name == spec["schema_name"],
                DataAsset.name == spec["name"],
            )
            .first()
        )
        if asset is None:
            columns = []
            for ordinal, column in enumerate(spec["columns"], start=1):
                columns.append(
                    {
                        "name": column["name"],
                        "data_type": column["data_type"],
                        "nullable": column.get("nullable", True),
                        "ordinal": ordinal,
                        "description": column.get("description"),
                    }
                )
            asset = DataAsset(
                owner_id=admin.id,
                name=spec["name"],
                asset_type=spec["asset_type"],
                database_name=DATABASE,
                schema_name=spec["schema_name"],
                columns_json=columns,
                description=spec["description"],
                status="active",
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
        index[asset.display_name] = asset
    return index


def _get_or_create_transformations(db, users, assets) -> list[Transformation]:
    created_or_parsed: list[Transformation] = []
    for spec in TRANSFORMATIONS:
        transformation = db.query(Transformation).filter(Transformation.name == spec["name"]).first()
        if transformation is None:
            owner = users[spec["owner"]]
            output_asset = assets[spec["output"]]
            input_assets = [assets[name] for name in spec["inputs"]]
            transformation = Transformation(
                owner_id=owner.id,
                name=spec["name"],
                dialect=spec["dialect"],
                sql_text=spec["sql"],
                input_asset_ids_json=[str(asset.id) for asset in input_assets],
                output_asset_id=output_asset.id,
                parse_status="pending",
                version=1,
                report_json={},
            )
            db.add(transformation)
            db.commit()
            db.refresh(transformation)
        edge_count = (
            db.query(LineageEdge)
            .filter(LineageEdge.transformation_id == transformation.id)
            .count()
        )
        # 已 parsed / partial 的 SQL 不重算；没有边的（首次或上次失败）才解析
        if transformation.parse_status in ("parsed", "partial") and edge_count > 0:
            created_or_parsed.append(transformation)
            continue
        if transformation.parse_status == "failed" and edge_count == 0:
            # seed 里不放“永远失败”的 SQL；历史失败记录允许重试一次
            pass
        transformation = parse_service.parse_transformation(db, transformation)
        created_or_parsed.append(transformation)
    return created_or_parsed


def _ensure_schema_change(db, assets) -> None:
    asset = assets["dwd.order_detail"]
    existing = (
        db.query(SchemaChangeEvent)
        .filter(
            SchemaChangeEvent.asset_id == asset.id,
            SchemaChangeEvent.column_name == "pay_amount",
            SchemaChangeEvent.change_type == ChangeType.change_type.value,
            SchemaChangeEvent.old_type == "decimal(18,2)",
            SchemaChangeEvent.new_type == "string",
        )
        .first()
    )
    if existing is not None:
        return
    db.add(
        SchemaChangeEvent(
            asset_id=asset.id,
            change_type=ChangeType.change_type.value,
            column_name="pay_amount",
            old_type="decimal(18,2)",
            new_type="string",
            source="manual",
        )
    )
    db.commit()
    log(
        logger,
        "SCHEMA_CHANGE_RECORDED",
        level=logging.INFO,
        asset=asset.full_name,
        column="pay_amount",
        change_type="change_type",
        old="decimal(18,2)",
        new="string",
    )


def _ensure_historical_impact(db, users, assets) -> ImpactAnalysis | None:
    asset = assets["dwd.order_detail"]
    existing = (
        db.query(ImpactAnalysis)
        .filter(
            ImpactAnalysis.target_asset_id == asset.id,
            ImpactAnalysis.target_column == "pay_amount",
            ImpactAnalysis.change_type == ChangeType.change_type.value,
        )
        .order_by(ImpactAnalysis.created_at.desc())
        .first()
    )
    if existing is not None:
        return existing
    analysis, _cached = impact_service.analyze(
        db,
        users["analyst"],
        target_asset_id=asset.id,
        target_column="pay_amount",
        change_type=ChangeType.change_type.value,
        force=True,
    )
    if analysis.affected_count != 5:
        logger.warning(
            "historical impact analysis affected_count=%s (expected 5) — 检查演示 SQL 与资产列清单",
            analysis.affected_count,
        )
    return analysis


def run_seed() -> dict:
    log(logger, "SEED_START", level=logging.INFO)
    db = SessionLocal()
    try:
        users = _get_or_create_users(db)
        assets = _get_or_create_assets(db, users["admin"])
        transformations = _get_or_create_transformations(db, users, assets)
        _ensure_schema_change(db, assets)
        analysis = _ensure_historical_impact(db, users, assets)

        summary = {
            "users": db.query(User).count(),
            "assets": db.query(DataAsset).count(),
            "transformations": db.query(Transformation).count(),
            "edges": db.query(LineageEdge).count(),
            "schema_changes": db.query(SchemaChangeEvent).count(),
            "impact_analyses": db.query(ImpactAnalysis).count(),
            "parse_status": {
                t.name: t.parse_status for t in transformations
            },
            "impact": {
                "severity": analysis.severity if analysis else None,
                "affected_count": analysis.affected_count if analysis else None,
            },
        }
        log(
            logger,
            "SEED_DONE",
            level=logging.INFO,
            users=summary["users"],
            assets=summary["assets"],
            transformations=summary["transformations"],
            edges=summary["edges"],
        )
        return summary
    finally:
        db.close()


def main() -> int:
    from app.config.logging import configure_logging

    configure_logging()
    summary = run_seed()
    print("SEED SUMMARY:", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
