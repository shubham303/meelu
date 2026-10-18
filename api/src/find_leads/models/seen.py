from datetime import datetime

from sqlalchemy import DateTime, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class LeadSeen(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "lead_seen"
    __table_args__ = (
        UniqueConstraint("site_id", "identity_key", name="lead_seen_site_identity_key"),
        Index("lead_seen_kind_seen_idx", "kind", "seen_at"),
    )

    identity_key: Mapped[str] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(nullable=False)
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
