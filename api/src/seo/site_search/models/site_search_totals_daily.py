from datetime import date

from sqlalchemy import REAL, Date, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteSearchTotalsDaily(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_search_totals_daily"
    __table_args__ = (
        Index("site_search_totals_daily_key_idx", "site_id", "day", "device", unique=True),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    device: Mapped[str] = mapped_column(nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    position: Mapped[float] = mapped_column(REAL, nullable=False)
    final: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
