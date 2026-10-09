from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import (
    EMPTY_JSON_ARRAY,
    EMPTY_TEXT_ARRAY,
    Base,
    EntityMixin,
    SiteScopedMixin,
)


class SiteCrawlJob(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_crawl_jobs"
    __table_args__ = (
        Index("site_crawl_jobs_site_idx", "site_id", "seq"),
        Index("site_crawl_jobs_status_idx", "status", "heartbeat_at"),
        Index(
            "site_crawl_jobs_active_idx",
            "site_id",
            unique=True,
            postgresql_where=text("status in ('queued', 'running', 'cancelling')"),
        ),
    )

    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'queued'"))
    trigger: Mapped[str] = mapped_column(nullable=False, server_default=text("'user'"))
    fresh_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cutoff_days: Mapped[int | None] = mapped_column(Integer)
    sitemap_urls: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    frontier: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    fetched: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    queued: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    new_pages: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    changed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    unchanged: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    pages_stored: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    passages_stored: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    error: Mapped[str | None]
    stop_reason: Mapped[str | None]
    notes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
