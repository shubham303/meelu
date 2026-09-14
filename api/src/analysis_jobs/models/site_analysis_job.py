from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteAnalysisJob(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_analysis_jobs"
    __table_args__ = (
        Index("site_analysis_jobs_site_idx", "site_id", "seq"),
        Index(
            "site_analysis_jobs_active_idx",
            "site_id",
            unique=True,
            postgresql_where=text("status in ('queued', 'running', 'cancelling')"),
        ),
    )

    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'queued'"))
    trigger: Mapped[str] = mapped_column(nullable=False, server_default=text("'user'"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    processed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    skipped_unchanged: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    skipped_similar: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error: Mapped[str | None]
    stop_reason: Mapped[str | None]
