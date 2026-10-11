from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class AnalyticsReport(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "analytics_reports"
    __table_args__ = (
        Index("analytics_reports_user_idx", "user_id", "created_at"),
        Index("analytics_reports_site_idx", "site_id", "created_at"),
    )

    title: Mapped[str] = mapped_column(nullable=False)
    html: Mapped[str] = mapped_column(nullable=False)
    created_by: Mapped[str] = mapped_column(nullable=False, server_default=text("'agent'"))
