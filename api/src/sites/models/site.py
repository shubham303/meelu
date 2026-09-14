from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, EMPTY_TEXT_ARRAY, Base, EntityMixin


class Site(EntityMixin, Base):
    __tablename__ = "site"
    __table_args__ = (
        Index("site_user_idx", "user_id"),
        Index("site_user_domain_idx", "user_id", "domain", unique=True),
    )

    domain: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str | None]
    repo_url: Mapped[str | None]
    summary: Mapped[str | None]
    social_links: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    sitemap_urls: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    sitemap_url_count: Mapped[int | None] = mapped_column(Integer)
    sitemap_at_root: Mapped[bool | None] = mapped_column(Boolean)
    robots_txt: Mapped[str | None]
    robots_status: Mapped[int | None] = mapped_column(Integer)
    robots_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    llms_txt: Mapped[str | None]
    llms_status: Mapped[int | None] = mapped_column(Integer)
    llms_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawler_access: Mapped[Any | None] = mapped_column(JSONB)
    host_variants: Mapped[Any | None] = mapped_column(JSONB)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gsc_property: Mapped[str | None]
    ga_property: Mapped[str | None]
