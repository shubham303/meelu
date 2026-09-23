from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class CreditLedgerEntry(EntityMixin, Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (Index("credit_ledger_user_idx", "user_id", "seq"),)

    kind: Mapped[str] = mapped_column(nullable=False)
    delta_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    provider_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_call.id", ondelete="SET NULL")
    )
    note: Mapped[str | None]
