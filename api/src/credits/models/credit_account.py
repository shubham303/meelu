from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class CreditAccount(Base):
    __tablename__ = "credit_account"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    balance_micros: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
