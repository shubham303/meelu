from datetime import date

from sqlalchemy import Date, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoRankHistory(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_rank_history"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "keyword",
            "location_code",
            "language_code",
            "observed_on",
            "url",
            name="seo_rank_history_key",
        ),
        Index("seo_rank_history_keyword_idx", "site_id", "keyword", "observed_on"),
    )

    keyword: Mapped[str] = mapped_column(nullable=False)
    location_code: Mapped[int] = mapped_column(Integer, nullable=False)
    language_code: Mapped[str] = mapped_column(nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    domain: Mapped[str] = mapped_column(nullable=False)
    is_site: Mapped[bool] = mapped_column(nullable=False)
    rank_group: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_absolute: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str | None]
