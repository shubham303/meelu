from datetime import date

from sqlalchemy import REAL, Date, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteTrafficChannelsDaily(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_traffic_channels_daily"
    __table_args__ = (
        Index(
            "site_traffic_channels_daily_key_idx",
            "site_id",
            "day",
            "channel",
            "source",
            "medium",
            unique=True,
        ),
        Index("site_traffic_channels_daily_channel_idx", "site_id", "channel", "day"),
        Index("site_traffic_channels_daily_day_idx", "site_id", "day"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    medium: Mapped[str] = mapped_column(nullable=False)
    sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    new_users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    engaged_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    key_events: Mapped[float] = mapped_column(REAL, nullable=False, server_default=text("0"))
    revenue: Mapped[float] = mapped_column(REAL, nullable=False, server_default=text("0"))
