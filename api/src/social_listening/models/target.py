from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SocialListeningTarget(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_target"
    __table_args__ = (
        UniqueConstraint(
            "site_id", "kind", "name", name="social_listening_target_site_kind_name_key"
        ),
        Index("social_listening_target_site_idx", "site_id", "seq"),
    )

    kind: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    source: Mapped[str] = mapped_column(nullable=False, server_default=text("'user'"))
