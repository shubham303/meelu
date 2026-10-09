from datetime import date

from sqlalchemy import Date, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoVolumeHistory(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_volume_history"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "keyword",
            "location_code",
            "language_code",
            "month",
            name="seo_volume_history_key",
        ),
        Index("seo_volume_history_keyword_idx", "site_id", "keyword", "month"),
    )

    keyword: Mapped[str] = mapped_column(nullable=False)
    location_code: Mapped[int] = mapped_column(Integer, nullable=False)
    language_code: Mapped[str] = mapped_column(nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    search_volume: Mapped[int | None] = mapped_column(Integer)
    clickstream_volume: Mapped[int | None] = mapped_column(Integer)
    cpc: Mapped[float | None]
    competition: Mapped[float | None]
