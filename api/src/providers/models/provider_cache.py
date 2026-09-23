from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, TimestampedMixin


class ProviderCache(TimestampedMixin, Base):
    __tablename__ = "provider_cache"
    __table_args__ = (Index("provider_cache_capability_idx", "domain", "capability", "fetched_at"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(nullable=False)
    capability: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    request: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict | list] = mapped_column(JSONB, nullable=False)
    vendor_cost_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
