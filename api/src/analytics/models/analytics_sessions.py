from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class AnalyticsSession(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "analytics_sessions"
    __table_args__ = (
        Index("analytics_sessions_user_idx", "user_id", "created_at"),
        Index("analytics_sessions_site_idx", "site_id", "created_at"),
    )

    title: Mapped[str] = mapped_column(nullable=False)
    about: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    session_key: Mapped[str | None]
