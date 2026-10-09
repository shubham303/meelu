from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_OBJECT, Base, EntityMixin, SiteScopedMixin


class SocialListeningRun(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_run"
    __table_args__ = (Index("social_listening_run_site_idx", "site_id", "seq"),)

    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'running'"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    kept_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    platform_stats: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    error: Mapped[str | None]
