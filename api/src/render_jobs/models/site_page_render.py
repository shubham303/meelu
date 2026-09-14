from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import (
    EMPTY_JSON_ARRAY,
    EMPTY_TEXT_ARRAY,
    Base,
    EntityMixin,
    SiteScopedMixin,
)


class SitePageRender(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_page_renders"
    __table_args__ = (
        Index("site_page_renders_page_device_idx", "page_id", "device", unique=True),
        Index("site_page_renders_site_idx", "site_id"),
    )

    page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    device: Mapped[str] = mapped_column(nullable=False, server_default=text("'desktop'"))
    rendered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    render_error: Mapped[str | None]
    user_agent_profile: Mapped[str] = mapped_column(
        nullable=False, server_default=text("'googlebot'")
    )
    rendered_from_hash: Mapped[str | None]
    final_url: Mapped[str | None]
    title: Mapped[str | None]
    meta_description: Mapped[str | None]
    canonical: Mapped[str | None]
    h1: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    robots_directives: Mapped[str | None]
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    internal_links: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    schema_types: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    content_hash: Mapped[str | None]
    console_errors: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    console_samples: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    failed_requests: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed_samples: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    blocked_assets: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    blocked_samples: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    js_bytes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    third_party_hosts: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    hidden_word_count: Mapped[int | None] = mapped_column(Integer)
    hidden_internal_links: Mapped[int | None] = mapped_column(Integer)
    viewport_overflow_px: Mapped[int | None] = mapped_column(Integer)
    small_tap_targets: Mapped[int | None] = mapped_column(Integer)
    html_path: Mapped[str | None]
