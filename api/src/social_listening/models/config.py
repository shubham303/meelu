from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class SocialListeningConfig(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_config"
    __table_args__ = (UniqueConstraint("site_id", name="social_listening_config_site_key"),)

    platforms: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
