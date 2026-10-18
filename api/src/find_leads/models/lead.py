from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class Lead(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "lead"
    __table_args__ = (
        UniqueConstraint("site_id", "identity_key", name="lead_site_identity_key"),
        Index("lead_site_status_idx", "site_id", "status"),
        Index("lead_run_idx", "run_id"),
    )

    brief_id: Mapped[str | None] = mapped_column(ForeignKey("lead_brief.id", ondelete="SET NULL"))
    run_id: Mapped[str | None] = mapped_column(ForeignKey("lead_run.id", ondelete="SET NULL"))
    identity_key: Mapped[str] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    platform: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str | None]
    handle: Mapped[str | None]
    headline: Mapped[str | None]
    profile_url: Mapped[str | None]
    email: Mapped[str | None]
    email_source_url: Mapped[str | None]
    website: Mapped[str | None]
    snippet: Mapped[str | None]
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    activity: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None]
    angle: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'candidate'"))
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
