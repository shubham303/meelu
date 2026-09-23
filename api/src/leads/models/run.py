from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_OBJECT, Base, EntityMixin, SiteScopedMixin


class LeadRun(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "lead_run"
    __table_args__ = (Index("lead_run_site_idx", "site_id", "seq"),)

    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("lead_campaign.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'running'"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    found: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    qualified: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    skipped_known: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    source_stats: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    error: Mapped[str | None]
