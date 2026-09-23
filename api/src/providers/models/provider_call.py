from sqlalchemy import BigInteger, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class ProviderCall(EntityMixin, Base):
    __tablename__ = "provider_call"
    __table_args__ = (Index("provider_call_user_idx", "user_id", "seq"),)

    site_id: Mapped[str | None] = mapped_column(ForeignKey("site.id", ondelete="SET NULL"))
    domain: Mapped[str] = mapped_column(nullable=False)
    capability: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str | None]
    cache_key: Mapped[str] = mapped_column(nullable=False)
    cache_hit: Mapped[bool] = mapped_column(nullable=False)
    vendor_cost_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    charged_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    error: Mapped[str | None]
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
