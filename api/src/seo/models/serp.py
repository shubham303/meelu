from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoSerpSnapshot(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_serp_snapshots"
    __table_args__ = (
        Index("seo_serp_snapshots_keyword_idx", "site_id", "keyword_id", "device", "fetched_at"),
    )

    keyword_id: Mapped[str] = mapped_column(
        ForeignKey("seo_keywords.id", ondelete="CASCADE"), nullable=False
    )
    device: Mapped[str] = mapped_column(nullable=False, server_default=text("'desktop'"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    features: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )


class SeoSerpResult(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_serp_results"
    __table_args__ = (Index("seo_serp_results_snapshot_idx", "snapshot_id", "rank"),)

    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("seo_serp_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    domain: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str | None]
    description: Mapped[str | None]
    is_ours: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
