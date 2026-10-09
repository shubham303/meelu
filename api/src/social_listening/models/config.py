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
    strictness: Mapped[str] = mapped_column(nullable=False, server_default=text("'balanced'"))
    max_age_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("365"))
