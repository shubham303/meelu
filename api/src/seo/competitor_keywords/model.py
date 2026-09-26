from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoCompetitorKeyword(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_competitor_keywords"
    __table_args__ = (
        UniqueConstraint("competitor_id", "keyword_id", name="seo_competitor_keywords_pair_key"),
        Index("seo_competitor_keywords_keyword_idx", "keyword_id"),
    )

    competitor_id: Mapped[str] = mapped_column(
        ForeignKey("seo_competitors.id", ondelete="CASCADE"), nullable=False
    )
    keyword_id: Mapped[str] = mapped_column(
        ForeignKey("seo_keywords.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None]
    etv: Mapped[float | None]
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
