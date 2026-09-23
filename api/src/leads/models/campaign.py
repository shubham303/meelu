from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class LeadCampaign(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "lead_campaign"
    __table_args__ = (
        UniqueConstraint("site_id", "name", name="lead_campaign_site_name_key"),
        Index("lead_campaign_site_idx", "site_id", "seq"),
    )

    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'active'"))
    audience: Mapped[str] = mapped_column(nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    schedule: Mapped[str | None]
