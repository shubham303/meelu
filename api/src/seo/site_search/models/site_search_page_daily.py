from datetime import date

from sqlalchemy import REAL, Date, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteSearchPageDaily(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_search_page_daily"
    __table_args__ = (
        Index("site_search_page_daily_key_idx", "site_id", "day", "page", unique=True),
        Index("site_search_page_daily_page_idx", "site_id", "page", "day"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    page: Mapped[str] = mapped_column(nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    position: Mapped[float] = mapped_column(REAL, nullable=False)
    final: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
