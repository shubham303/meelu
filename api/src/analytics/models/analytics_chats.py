from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class AnalyticsChat(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "analytics_chats"
    __table_args__ = (Index("analytics_chats_site_idx", "user_id", "site_id", "updated_at"),)

    title: Mapped[str] = mapped_column(nullable=False)
    sdk_session_id: Mapped[str | None] = mapped_column(nullable=True)
