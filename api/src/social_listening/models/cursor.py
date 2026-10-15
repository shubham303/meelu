from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SocialListeningCursor(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_cursor"
    __table_args__ = (
        UniqueConstraint(
            "site_id", "platform", "keyword", name="social_listening_cursor_site_keyword_key"
        ),
    )

    platform: Mapped[str] = mapped_column(nullable=False)
    keyword: Mapped[str] = mapped_column(nullable=False)
    last_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
