from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, Boolean, DateTime, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin
from src.seo.site_seo.constants import (
    GENUINE_ITEM_TYPES,
    GENUINE_MAX_DOMAIN_SPAM_SCORE,
    GENUINE_MAX_EXTERNAL_LINKS,
    GENUINE_MAX_LINKS_FROM_DOMAIN,
    GENUINE_MAX_SPAM_SCORE,
    GENUINE_MIN_DOMAIN_RANK,
    PAID_LINK_ATTRIBUTES,
    PAID_PLACEMENT,
)


class SiteBacklink(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_backlinks"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "site_domain",
            "backlinking_url",
            "backlink_url",
            name="site_backlinks_key",
        ),
        Index("site_backlinks_target_idx", "site_id", "site_domain"),
        Index("site_backlinks_linking_idx", "site_id", "backlinking_domain"),
    )

    site_domain: Mapped[str] = mapped_column(nullable=False)
    backlink_url: Mapped[str] = mapped_column(nullable=False)
    backlinking_domain: Mapped[str] = mapped_column(nullable=False)
    backlinking_url: Mapped[str] = mapped_column(nullable=False)

    anchor: Mapped[str | None]
    item_type: Mapped[str | None]
    dofollow: Mapped[bool | None]
    link_attributes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    semantic_location: Mapped[str | None]
    links_from_domain: Mapped[int | None] = mapped_column(Integer)
    is_lost: Mapped[bool | None]
    is_broken: Mapped[bool | None]
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    backlink_spam_score: Mapped[int | None] = mapped_column(Integer)
    domain_spam_score: Mapped[int | None] = mapped_column(Integer)
    domain_rank: Mapped[int | None] = mapped_column(Integer)
    page_rank: Mapped[int | None] = mapped_column(Integer)
    is_ip: Mapped[bool | None]
    platform_type: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    country: Mapped[str | None]
    page_title: Mapped[str | None]
    page_language: Mapped[str | None]
    page_status_code: Mapped[int | None] = mapped_column(Integer)
    page_external_links: Mapped[int | None] = mapped_column(Integer)

    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


def is_spam(row: Mapping[str, Any]) -> bool:
    spam = row.get("backlink_spam_score")
    domain_spam = row.get("domain_spam_score")
    return (
        spam is None
        or spam > GENUINE_MAX_SPAM_SCORE
        or (domain_spam is not None and domain_spam > GENUINE_MAX_DOMAIN_SPAM_SCORE)
        or (row.get("page_external_links") or 0) > GENUINE_MAX_EXTERNAL_LINKS
        or bool(row.get("is_ip"))
    )


def is_paid(row: Mapping[str, Any]) -> bool:
    attributes = {a.lower() for a in row.get("link_attributes") or []}
    placement = f"{row.get('page_title') or ''} {row.get('backlinking_url') or ''}"
    return (
        bool(attributes & PAID_LINK_ATTRIBUTES)
        or bool(PAID_PLACEMENT.search(placement))
        or (row.get("links_from_domain") or 0) > GENUINE_MAX_LINKS_FROM_DOMAIN
    )


def is_weak(row: Mapping[str, Any]) -> bool:
    return (
        (row.get("domain_rank") or 0) < GENUINE_MIN_DOMAIN_RANK
        or row.get("page_status_code") not in (None, 200)
        or row.get("item_type") not in GENUINE_ITEM_TYPES
        or bool(row.get("is_lost"))
        or bool(row.get("is_broken"))
    )


def is_genuine(row: Mapping[str, Any]) -> bool:
    return not (is_spam(row) or is_paid(row) or is_weak(row))
