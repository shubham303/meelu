from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class Prospect(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "prospects"
    __table_args__ = (
        Index("prospects_user_idx", "user_id", "created_at"),
        Index("prospects_campaign_idx", "campaign_id"),
        Index("prospects_dedupe_idx", "dedupe_keys", postgresql_using="gin"),
    )

    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    company: Mapped[str | None]
    role: Mapped[str | None]
    email: Mapped[str | None]
    website: Mapped[str | None]
    source_url: Mapped[str | None]
    fit_reason: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'found'"))
    dedupe_keys: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
