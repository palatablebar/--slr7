"""DataAsset 模型。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class DataAsset(Base):
    __tablename__ = "data_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, default="table")
    database_name: Mapped[str] = mapped_column(String(64), nullable=False, default="lanzo_dw")
    schema_name: Mapped[str] = mapped_column(String(64), nullable=False, default="public")
    columns_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner = relationship("User", back_populates="assets", foreign_keys=[owner_id])
    schema_changes = relationship("SchemaChangeEvent", back_populates="asset")
    outgoing_edges = relationship(
        "LineageEdge", back_populates="source_asset", foreign_keys="LineageEdge.source_asset_id"
    )
    incoming_edges = relationship(
        "LineageEdge", back_populates="target_asset", foreign_keys="LineageEdge.target_asset_id"
    )

    @property
    def display_name(self) -> str:
        return f"{self.schema_name}.{self.name}"

    @property
    def full_name(self) -> str:
        return f"{self.database_name}.{self.schema_name}.{self.name}"
