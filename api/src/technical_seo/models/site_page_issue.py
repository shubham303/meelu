from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SitePageIssue(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_page_issues"
    __table_args__ = (
        UniqueConstraint("run_id", "page_id", "kind", name="site_page_issues_kind_idx"),
        Index("site_page_issues_run_state_idx", "run_id", "state"),
        Index("site_page_issues_run_kind_idx", "run_id", "kind"),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("site_audit_runs.id", ondelete="CASCADE"), nullable=False
    )
    page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(nullable=False)
    issue: Mapped[str] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(nullable=False, server_default=text("'p2'"))
    matched_pages: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'open'"))
    rejection_reason: Mapped[str | None]
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issue_type: Mapped[str] = mapped_column(nullable=False, server_default=text("'static'"))
    llm_check_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    llm_check_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
