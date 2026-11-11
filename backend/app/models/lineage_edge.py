"""LineageEdge 模型（列级）。"""
from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class LineageEdge(Base):
    __tablename__ = "lineage_edges"
    __table_args__ = (
        UniqueConstraint(
            "transformation_id", "source_column", "target_column", name="uq_edge_transform_columns"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transformation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transformations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False, index=True
    )
    source_column: Mapped[str] = mapped_column(String(128), nullable=False)
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False, index=True
    )
    target_column: Mapped[str] = mapped_column(String(128), nullable=False)
    edge_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="direct")
    expression_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    transformation = relationship("Transformation", back_populates="edges")
    source_asset = relationship("DataAsset", back_populates="outgoing_edges", foreign_keys=[source_asset_id])
    target_asset = relationship("DataAsset", back_populates="incoming_edges", foreign_keys=[target_asset_id])
