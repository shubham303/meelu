from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SocialAccount(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        Index("social_accounts_site_idx", "site_id", unique=True),
        Index("social_accounts_provider_idx", "provider", "external_account_id"),
    )

    provider: Mapped[str] = mapped_column(nullable=False)
    external_account_id: Mapped[str] = mapped_column(nullable=False)
