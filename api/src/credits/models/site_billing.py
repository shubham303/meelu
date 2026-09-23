from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class SiteBilling(Base):
    __tablename__ = "site_billing"
    __table_args__ = (Index("site_billing_due_idx", "last_charged_at"),)

    site_id: Mapped[str] = mapped_column(
        ForeignKey("site.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    last_charged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    charge_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    charged_micros: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
