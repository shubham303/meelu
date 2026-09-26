from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoCompetitor(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_competitors"
    __table_args__ = (
        UniqueConstraint("site_id", "domain", name="seo_competitors_site_domain_key"),
        Index("seo_competitors_state_idx", "site_id", "state"),
    )

    domain: Mapped[str] = mapped_column(nullable=False)
    brand_terms: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    first_source: Mapped[str] = mapped_column(nullable=False)
    intersections: Mapped[int | None] = mapped_column(Integer)
    avg_position: Mapped[float | None]
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'candidate'"))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
