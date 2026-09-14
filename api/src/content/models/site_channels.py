from sqlalchemy import Boolean, Index, Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class SiteChannel(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_channels"
    __table_args__ = (
        Index("site_channels_site_channel_idx", "site_id", "channel_key", unique=True),
    )

    channel_key: Mapped[str] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    rules: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    timezone: Mapped[str] = mapped_column(nullable=False, server_default=text("'UTC'"))
    posting_windows: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    min_gap_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("24"))
