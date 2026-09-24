from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoPageFacts(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_page_facts"
    __table_args__ = (
        Index("seo_page_facts_page_idx", "page_id", unique=True),
        Index("seo_page_facts_site_idx", "site_id", "live"),
    )

    page_id: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[int | None] = mapped_column(Integer)
    redirect_to: Mapped[str | None]
    page_type: Mapped[str | None]
    lang: Mapped[str | None]
    title: Mapped[str | None]
    h1: Mapped[str | None]
    headings: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    meta_description: Mapped[str | None]
    title_pixels: Mapped[int | None] = mapped_column(Integer)
    word_count: Mapped[int | None] = mapped_column(Integer)
    inlinks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    link_score: Mapped[float | None]
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None]
    indexable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    live: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    impressions_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    clicks_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions_ly_28d: Mapped[int | None] = mapped_column(Integer)
    clicks_ly_28d: Mapped[int | None] = mapped_column(Integer)
