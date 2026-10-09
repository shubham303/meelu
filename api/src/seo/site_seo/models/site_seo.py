from sqlalchemy import ARRAY, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SiteSeo(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_seo"
    __table_args__ = (UniqueConstraint("site_id", name="site_seo_site_key"),)

    backlink_opportunities: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
