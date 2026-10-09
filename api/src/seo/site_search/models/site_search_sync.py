from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Index, Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class SiteSearchSync(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_search_syncs"
    __table_args__ = (
        Index("site_search_syncs_site_idx", "site_id", "seq"),
        Index(
            "site_search_syncs_active_idx",
            "site_id",
            unique=True,
            postgresql_where=text("status in ('queued', 'running')"),
        ),
    )

    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'queued'"))
    trigger: Mapped[str] = mapped_column(nullable=False, server_default=text("'user'"))
    property: Mapped[str | None]
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    days_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    days_done: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    rows_stored: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    pages_inspected: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    first_day: Mapped[date | None] = mapped_column(Date)
    last_day: Mapped[date | None] = mapped_column(Date)
    error: Mapped[str | None]
    notes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
