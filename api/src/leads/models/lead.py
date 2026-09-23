from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import (
    EMPTY_JSON_ARRAY,
    EMPTY_JSON_OBJECT,
    Base,
    EntityMixin,
    SiteScopedMixin,
)


class Lead(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "lead"
    __table_args__ = (Index("lead_site_idx", "site_id", "seq"),)

    campaign_id: Mapped[str | None] = mapped_column(
        ForeignKey("lead_campaign.id", ondelete="SET NULL")
    )
    run_id: Mapped[str | None] = mapped_column(ForeignKey("lead_run.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(nullable=False)
    company: Mapped[str | None]
    role: Mapped[str | None]
    email: Mapped[str | None]
    email_verified: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    website: Mapped[str | None]
    source: Mapped[str | None]
    source_url: Mapped[str | None]
    channel_handles: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    fit_score: Mapped[float | None]
    fit_reason: Mapped[str | None]
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    stage: Mapped[str] = mapped_column(nullable=False, server_default=text("'qualified'"))
    stage_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None]
    dedupe_keys: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
