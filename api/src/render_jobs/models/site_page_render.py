from datetime import datetime
from typing import Any

from sqlalchemy import REAL, Boolean, DateTime, ForeignKey, Index, Integer, text
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
    status: Mapped[int | None] = mapped_column(Integer)
    document_bytes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    html_bytes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    settle_reason: Mapped[str | None]
    pending_requests: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    pending_samples: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    main_frame_navigations: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    visible_word_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    exception_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    soft404_signal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    service_worker: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    internal_link_urls: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    external_link_hosts: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    uncrawlable_anchors: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    uncrawlable_nav_anchors: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    uncrawlable_samples: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    hashbang_links: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    meta_fragment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    dangling_fragment_links: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    load_more_control: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    pagination_links: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    images: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    images_without_src: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    images_without_src_above_fold: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    shadow_dom_words: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    plugin_content: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    title_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    description_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    canonical_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    canonical_hrefs: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    robots_meta_contents: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    schema_blocks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    schema_invalid_blocks: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    schema_hashes: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    hreflang: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    hreflang_invalid: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    social_meta_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    nosnippet_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    template_tokens_head: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    template_tokens_body: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    viewport_meta: Mapped[str | None]
    failed_data_requests: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    failed_data_samples: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    failed_scripts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed_script_samples: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    cors_errors: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    websocket_used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    mixed_content_active: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    mixed_content_passive: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    largest_resource_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    largest_resource_url: Mapped[str | None]
    overlay_coverage: Mapped[float | None] = mapped_column(REAL)
    overlay_sample: Mapped[str | None]
    small_text_ratio: Mapped[float | None] = mapped_column(REAL)
    text_chars: Mapped[int | None] = mapped_column(Integer)
    html_path: Mapped[str | None]
