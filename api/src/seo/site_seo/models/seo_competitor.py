from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoCompetitor(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_competitors"
    __table_args__ = (
        UniqueConstraint("site_id", "domain", name="seo_competitors_key"),
        Index("seo_competitors_site_idx", "site_id", "created_at"),
    )

    domain: Mapped[str] = mapped_column(nullable=False)
