from datetime import date

from sqlalchemy import REAL, Date, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteSearchDaily(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_search_daily"
    __table_args__ = (
        Index(
            "site_search_daily_key_idx",
            "site_id",
            "day",
            "query",
            "page",
            "device",
            "country",
            unique=True,
        ),
        Index("site_search_daily_page_idx", "site_id", "page", "day"),
        Index("site_search_daily_query_idx", "site_id", "query", "day"),
        Index("site_search_daily_day_idx", "site_id", "day"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    query: Mapped[str] = mapped_column(nullable=False)
    page: Mapped[str] = mapped_column(nullable=False)
    device: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    position: Mapped[float] = mapped_column(REAL, nullable=False)
