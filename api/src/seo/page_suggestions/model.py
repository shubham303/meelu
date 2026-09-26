from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_OBJECT, EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoPageSuggestion(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_page_suggestions"
    __table_args__ = (
        Index(
            "seo_page_suggestions_add_key",
            "site_id",
            "action",
            "topic_key",
            unique=True,
            postgresql_where=text("page_id IS NULL"),
        ),
        Index(
            "seo_page_suggestions_page_key",
            "site_id",
            "action",
            "page_id",
            "topic_key",
            unique=True,
            postgresql_where=text("page_id IS NOT NULL"),
        ),
        Index("seo_page_suggestions_job_idx", "job_id"),
        Index("seo_page_suggestions_state_idx", "site_id", "state"),
        Index("seo_page_suggestions_pair_idx", "pair_id"),
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("seo_jobs.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(nullable=False)
    page_id: Mapped[str | None]
    topic_key: Mapped[str] = mapped_column(nullable=False)
    cluster_id: Mapped[str | None] = mapped_column(
        ForeignKey("seo_keyword_clusters.id", ondelete="SET NULL")
    )
    pair_id: Mapped[str | None] = mapped_column(
        ForeignKey("seo_page_suggestions.id", ondelete="SET NULL")
    )
    merge_into_page_id: Mapped[str | None]
    strategies: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    suggestion: Mapped[str] = mapped_column(nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    coverage_at_creation: Mapped[float | None]
    impressions_at_creation: Mapped[int | None]
    target_position: Mapped[float | None]
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'draft'"))
    search_score: Mapped[float | None]
    confidence: Mapped[float | None]
    score: Mapped[float | None]
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
