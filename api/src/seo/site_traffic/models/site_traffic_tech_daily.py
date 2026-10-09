from datetime import date

from sqlalchemy import Date, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteTrafficTechDaily(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_traffic_tech_daily"
    __table_args__ = (
        Index(
            "site_traffic_tech_daily_key_idx",
            "site_id",
            "day",
            "device_category",
            "os",
            "browser",
            unique=True,
        ),
        Index("site_traffic_tech_daily_day_idx", "site_id", "day"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    device_category: Mapped[str] = mapped_column(nullable=False)
    os: Mapped[str] = mapped_column(nullable=False)
    browser: Mapped[str] = mapped_column(nullable=False)
    sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
