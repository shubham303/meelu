from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoCompetitor(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_competitors"
    __table_args__ = (
        UniqueConstraint("site_id", "domain", name="seo_competitors_site_domain_key"),
        Index("seo_competitors_state_idx", "site_id", "state"),
    )

    domain: Mapped[str] = mapped_column(nullable=False)
    brand_terms: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    first_source: Mapped[str] = mapped_column(nullable=False)
    intersections: Mapped[int | None] = mapped_column(Integer)
    avg_position: Mapped[float | None]
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'candidate'"))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
