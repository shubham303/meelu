from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class AnalyticsSource(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "analytics_sources"
    __table_args__ = (
        Index("analytics_sources_user_idx", "user_id", "created_at"),
        Index("analytics_sources_session_idx", "session_id", "created_at"),
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("analytics_sessions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    file_path: Mapped[str | None]
