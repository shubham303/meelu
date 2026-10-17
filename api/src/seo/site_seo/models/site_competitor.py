from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, UniqueConstraint, and_
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from src.core.orm import Base, EntityMixin, SiteScopedMixin
from src.seo.site_seo.models.site_backlink import SiteBacklink


class SiteCompetitor(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_competitors"
    __table_args__ = (
        UniqueConstraint("site_id", "domain", name="site_competitors_key"),
        Index("site_competitors_site_idx", "site_id", "created_at"),
    )

    domain: Mapped[str] = mapped_column(nullable=False)
    domain_rank: Mapped[int | None] = mapped_column(Integer)
    backlinks_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    backlinks: Mapped[list[SiteBacklink]] = relationship(
        SiteBacklink,
        primaryjoin=lambda: and_(
            SiteCompetitor.site_id == foreign(SiteBacklink.site_id),
            SiteCompetitor.domain == foreign(SiteBacklink.site_domain),
        ),
        viewonly=True,
        lazy="raise",
    )
