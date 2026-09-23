from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteRenderJob(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_render_jobs"
    __table_args__ = (
        Index("site_render_jobs_site_idx", "site_id", "seq"),
        Index(
            "site_render_jobs_active_idx",
            "site_id",
            unique=True,
            postgresql_where=text("status in ('queued', 'running', 'cancelling')"),
        ),
    )

    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'queued'"))
    trigger: Mapped[str] = mapped_column(nullable=False, server_default=text("'user'"))
    scope: Mapped[str] = mapped_column(nullable=False, server_default=text("'sample'"))
    page_limit: Mapped[int | None] = mapped_column(Integer)
    page_url: Mapped[str | None]
    device: Mapped[str] = mapped_column(nullable=False, server_default=text("'desktop'"))
    user_agent_profile: Mapped[str] = mapped_column(
        nullable=False, server_default=text("'googlebot'")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    rendered: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error: Mapped[str | None]
    stop_reason: Mapped[str | None]
