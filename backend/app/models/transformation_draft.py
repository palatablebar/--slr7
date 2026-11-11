"""TransformationDraft 模型：未上线的编辑草稿。

草稿与已上线的 Transformation 严格分离：
- 草稿 SQL / 输入输出资产 / 方言的修改只落在本表；
- 草稿解析状态（parse_status / parse_error / report_json）仅描述草稿，
  不影响 Transformation 上已上线版本的状态；
- 只有草稿解析通过（parsed / partial）后，才会在单个事务内把内容与
  血缘边整体切换到 Transformation；解析失败（failed）时血缘边一律不动。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class TransformationDraft(Base):
    __tablename__ = "transformation_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transformation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transformations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # 草稿内容（上线前不回写 transformations 主表）
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    dialect: Mapped[str] = mapped_column(String(24), nullable=False, default="postgres")
    input_asset_ids_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    output_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False
    )
    # 草稿级解析状态：只描述草稿，绝不代表已上线版本
    parse_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_line: Mapped[int | None] = mapped_column(nullable=True)
    error_column: Mapped[int | None] = mapped_column(nullable=True)
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    transformation = relationship("Transformation", back_populates="draft")
