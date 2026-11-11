"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-09

首个迁移：直接使用 ORM metadata 建全部表（模型是唯一事实来源，
后续字段变更按 alembic revision 逐步补充）。

注意：后续 revision 新增的表（如 0002 的 transformation_drafts）会从
本迁移的 create_all / drop_all 中排除，避免空库顺序升级时被提前建出
而与后续显式建表的 revision 冲突。
"""
from __future__ import annotations

from alembic import op

from app.config.database import Base
from app import models  # noqa: F401  注册全部模型

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# 由后续 migration 引入的表：空库升级到 0001 时不应包含它们，
# 否则会与 0002 等显式建表的 revision 冲突。
_INTRODUCED_LATER = {"transformation_drafts"}


def upgrade() -> None:
    tables = [table for name, table in Base.metadata.tables.items() if name not in _INTRODUCED_LATER]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    tables = [table for name, table in Base.metadata.tables.items() if name not in _INTRODUCED_LATER]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables)
