"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-09

首个迁移：直接使用 ORM metadata 建全部表（模型是唯一事实来源，
后续字段变更按 alembic revision 逐步补充）。
"""
from __future__ import annotations

from alembic import op

from app.config.database import Base
from app import models  # noqa: F401  注册全部模型

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
