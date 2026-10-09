from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class Payment(EntityMixin, Base):
    __tablename__ = "payment"
    __table_args__ = (Index("payment_user_idx", "user_id", "seq"),)

    status: Mapped[str] = mapped_column(nullable=False)
    credit_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checkout_session_id: Mapped[str | None] = mapped_column(unique=True)
    checkout_url: Mapped[str | None]
    dodo_payment_id: Mapped[str | None] = mapped_column(unique=True)
    paid_amount: Mapped[int | None] = mapped_column(Integer)
    paid_currency: Mapped[str | None]
    credited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
