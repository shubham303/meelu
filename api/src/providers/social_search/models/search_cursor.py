from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, TimestampedMixin


class SocialSearchCursor(TimestampedMixin, Base):
    __tablename__ = "social_search_cursor"
    __table_args__ = (
        UniqueConstraint("platform", "keyword", name="social_search_cursor_platform_keyword_key"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(nullable=False)
    keyword: Mapped[str] = mapped_column(nullable=False)
    last_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
