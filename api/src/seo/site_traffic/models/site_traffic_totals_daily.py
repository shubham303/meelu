from datetime import date

from sqlalchemy import REAL, Date, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteTrafficTotalsDaily(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_traffic_totals_daily"
    __table_args__ = (Index("site_traffic_totals_daily_key_idx", "site_id", "day", unique=True),)

    day: Mapped[date] = mapped_column(Date, nullable=False)
    users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    new_users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    engaged_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    page_views: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    engagement_seconds: Mapped[float] = mapped_column(
        REAL, nullable=False, server_default=text("0")
    )
    key_events: Mapped[float] = mapped_column(REAL, nullable=False, server_default=text("0"))
    revenue: Mapped[float] = mapped_column(REAL, nullable=False, server_default=text("0"))
