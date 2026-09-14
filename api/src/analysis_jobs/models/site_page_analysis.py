from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import (
    EMPTY_JSON_ARRAY,
    EMPTY_TEXT_ARRAY,
    Base,
    EntityMixin,
    SiteScopedMixin,
)


class SitePageAnalysis(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_page_analysis"
    __table_args__ = (
        Index("site_page_analysis_page_idx", "page_id", unique=True),
        Index("site_page_analysis_site_idx", "site_id"),
    )

    page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    topics: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    questions_answered: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    analyzed_from_hash: Mapped[str | None]
    analyzed_text: Mapped[str | None]
    model: Mapped[str | None]
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
