"""transformation_drafts

Revision ID: 0002_drafts
Revises: 0001_initial
Create Date: 2026-11-11

新增转换草稿表 transformation_drafts：未上线的编辑与草稿级解析状态
独立存放，解析失败不影响 transformations 主表的已上线血缘。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_drafts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _uuid_column() -> sa.TypeEngine:
    # 本地 SQLite 测试与生产 PostgreSQL 都能执行
    return sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()
    op.create_table(
        "transformation_drafts",
        sa.Column("id", _uuid_column(), primary_key=True),
        sa.Column(
            "transformation_id",
            _uuid_column(),
            sa.ForeignKey("transformations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("updated_by_id", _uuid_column(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sql_text", sa.Text(), nullable=False),
        sa.Column("dialect", sa.String(length=24), nullable=False, server_default="postgres"),
        sa.Column("input_asset_ids_json", json_type, nullable=False),
        sa.Column(
            "output_asset_id",
            _uuid_column(),
            sa.ForeignKey("data_assets.id"),
            nullable=False,
        ),
        sa.Column("parse_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("error_line", sa.Integer(), nullable=True),
        sa.Column("error_column", sa.Integer(), nullable=True),
        sa.Column("report_json", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_transformation_drafts_transformation_id",
        "transformation_drafts",
        ["transformation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transformation_drafts_transformation_id", table_name="transformation_drafts")
    op.drop_table("transformation_drafts")
