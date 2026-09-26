from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoKeywordGscPage(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_keyword_gsc_pages"
    __table_args__ = (
        UniqueConstraint("keyword_id", "page_id", name="seo_keyword_gsc_pages_pair_key"),
        Index("seo_keyword_gsc_pages_page_idx", "site_id", "page_id"),
        Index("seo_keyword_gsc_pages_keyword_idx", "site_id", "keyword_id"),
    )

    keyword_id: Mapped[str] = mapped_column(
        ForeignKey("seo_keywords.id", ondelete="CASCADE"), nullable=False
    )
    page_id: Mapped[str] = mapped_column(nullable=False)
    position: Mapped[float | None]
    impressions_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    clicks_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions_prev_28d: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    clicks_prev_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions_ly_28d: Mapped[int | None] = mapped_column(Integer)
    clicks_ly_28d: Mapped[int | None] = mapped_column(Integer)
    ctr: Mapped[float | None]
    ctr_gap: Mapped[float | None]
    leader_days_90d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    coverage: Mapped[float | None]
    lexical_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
