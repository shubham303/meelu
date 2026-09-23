from sqlalchemy import Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class SocialListeningConfig(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_config"
    __table_args__ = (UniqueConstraint("site_id", name="social_listening_config_site_key"),)

    platforms: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    results_per_keyword: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("50")
    )
    min_relevance: Mapped[float] = mapped_column(nullable=False, server_default=text("0.6"))
    min_similarity: Mapped[float] = mapped_column(nullable=False, server_default=text("0.8"))
    max_age_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("365"))
    drop_dead_posts: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    schedule: Mapped[str | None]
