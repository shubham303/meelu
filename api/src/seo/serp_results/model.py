from sqlalchemy import Boolean, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


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
