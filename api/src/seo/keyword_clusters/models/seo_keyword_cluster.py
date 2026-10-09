from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, DateTime, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoKeywordCluster(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_keyword_clusters"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "location_code",
            "language_code",
            "main_keyword",
            name="seo_keyword_clusters_key",
        ),
        Index("seo_keyword_clusters_rank_idx", "site_id", "winnability", "volume"),
    )

    main_keyword: Mapped[str] = mapped_column(nullable=False)
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    core_keyword: Mapped[str | None]
    seeds: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    location_code: Mapped[int] = mapped_column(Integer, nullable=False)
    language_code: Mapped[str] = mapped_column(nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    winnability: Mapped[float | None]
    p_top_three: Mapped[float | None]
    p_page_one: Mapped[float | None]
    likely_position: Mapped[int | None] = mapped_column(Integer)
    our_position: Mapped[int | None] = mapped_column(Integer)
    our_url: Mapped[str | None]
    our_strength: Mapped[float | None]
    intent_fit: Mapped[float | None]
    is_ranked: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    climb: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    metrics_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
