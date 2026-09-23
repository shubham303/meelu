from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteIssue(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_issues"
    __table_args__ = (
        UniqueConstraint("run_id", "kind", name="site_issues_kind_idx"),
        Index("site_issues_run_state_idx", "run_id", "state"),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("site_audit_runs.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(nullable=False)
    issue: Mapped[str] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(nullable=False, server_default=text("'p2'"))
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'open'"))
    rejection_reason: Mapped[str | None]
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issue_type: Mapped[str] = mapped_column(nullable=False, server_default=text("'static'"))
