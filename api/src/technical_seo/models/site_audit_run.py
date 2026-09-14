from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteAuditRun(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_audit_runs"
    __table_args__ = (Index("site_audit_runs_site_idx", "site_id", "seq"),)

    trigger: Mapped[str] = mapped_column(nullable=False, server_default=text("'user'"))
    rules_run: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    site_issues_found: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    page_issues_found: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
