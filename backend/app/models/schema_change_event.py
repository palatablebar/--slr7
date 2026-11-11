"""SchemaChangeEvent 模型。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class SchemaChangeEvent(Base):
    __tablename__ = "schema_change_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False, index=True
    )
    change_type: Mapped[str] = mapped_column(String(24), nullable=False)
    column_name: Mapped[str] = mapped_column(String(128), nullable=False)
    old_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")

    asset = relationship("DataAsset", back_populates="schema_changes")
