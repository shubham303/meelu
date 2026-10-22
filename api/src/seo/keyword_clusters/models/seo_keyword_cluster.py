from sqlalchemy import ARRAY, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoKeywordCluster(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_keyword_clusters"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "location_code",
            "language_code",
            "main_keyword",
            name="seo_keyword_clusters_key",
        ),
        Index("seo_keyword_clusters_volume_idx", "site_id", "volume"),
        Index("seo_keyword_clusters_intent_idx", "site_id", "intent"),
        Index("seo_keyword_clusters_importance_idx", "site_id", "importance"),
    )

    main_keyword: Mapped[str] = mapped_column(nullable=False)
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    core_keyword: Mapped[str | None]
    seeds: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    location_code: Mapped[int] = mapped_column(Integer, nullable=False)
    language_code: Mapped[str] = mapped_column(nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    intent: Mapped[str | None]
    importance: Mapped[str | None]
    is_brand_keyword: Mapped[bool | None]
    is_ranked: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
