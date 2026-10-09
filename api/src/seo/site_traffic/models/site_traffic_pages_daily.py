from datetime import date

from sqlalchemy import REAL, Date, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteTrafficPagesDaily(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_traffic_pages_daily"
    __table_args__ = (
        Index(
            "site_traffic_pages_daily_key_idx",
            "site_id",
            "day",
            "page_path",
            unique=True,
        ),
        Index("site_traffic_pages_daily_page_idx", "site_id", "page_path", "day"),
        Index("site_traffic_pages_daily_day_idx", "site_id", "day"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    page_path: Mapped[str] = mapped_column(nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    engagement_seconds: Mapped[float] = mapped_column(
        REAL, nullable=False, server_default=text("0")
    )
    key_events: Mapped[float] = mapped_column(REAL, nullable=False, server_default=text("0"))
