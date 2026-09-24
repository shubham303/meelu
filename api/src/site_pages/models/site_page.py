from datetime import datetime
from typing import Any

from sqlalchemy import REAL, Boolean, DateTime, Index, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import (
    EMPTY_JSON_ARRAY,
    EMPTY_JSON_OBJECT,
    EMPTY_TEXT_ARRAY,
    Base,
    EntityMixin,
    SiteScopedMixin,
)


class SitePage(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_pages"
    __table_args__ = (
        Index("site_pages_site_url_idx", "site_id", "url", unique=True),
        Index("site_pages_stage_idx", "site_id", "status", "shallow"),
        Index("site_pages_freshness_idx", "site_id", "last_crawled_at"),
        Index("site_pages_sitemap_idx", "site_id", "in_sitemap"),
        Index("site_pages_depth_idx", "site_id", "depth"),
        Index("site_pages_site_inlinks_idx", "site_id", "inlinks"),
        Index("site_pages_site_words_idx", "site_id", "word_count"),
        Index("site_pages_site_content_changed_idx", "site_id", "content_changed_at"),
        Index("site_pages_site_blocked_idx", "site_id", "blocked_by_robots"),
        Index(
            "site_pages_url_trgm_idx",
            "url",
            postgresql_using="gin",
            postgresql_ops={"url": "gin_trgm_ops"},
        ),
    )

    url: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None]
    etag: Mapped[str | None]
    last_modified: Mapped[str | None]
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inlinks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    title: Mapped[str | None]
    title_pixels: Mapped[int | None] = mapped_column(Integer)
    meta_description: Mapped[str | None]
    h1: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    headings: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    body_text: Mapped[str | None]
    canonical: Mapped[str | None]
    robots_directives: Mapped[str | None]
    x_robots_tag: Mapped[str | None]
    blocked_by_robots: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    viewport_meta: Mapped[str | None]
    nosnippet_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    has_google_analytics: Mapped[bool | None] = mapped_column(Boolean)
    social_meta_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    social_meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    author: Mapped[str | None]
    schema_types: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    schema_nodes: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    lang: Mapped[str | None]
    hreflang: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    format: Mapped[str | None]
    in_sitemap: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    depth: Mapped[int | None] = mapped_column(Integer)
    redirect_to: Mapped[str | None]
    redirect_final: Mapped[str | None]
    redirect_hops: Mapped[int | None] = mapped_column(Integer)
    fetch_error: Mapped[str | None]
    content_type: Mapped[str | None]
    images: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    word_count: Mapped[int | None] = mapped_column(Integer)
    mixed_content: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    link_score: Mapped[float | None] = mapped_column(REAL)
    chunked_from_hash: Mapped[str | None]
    embed_state: Mapped[str | None]
    embed_error: Mapped[str | None]
    shallow: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    shallow_reason: Mapped[str | None]
    visited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
