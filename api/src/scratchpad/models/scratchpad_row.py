from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class ScratchpadRow(Base):
    __tablename__ = "scratchpad_row"
    __table_args__ = (
        UniqueConstraint("scratchpad_id", "text_hash", name="scratchpad_row_hash_key"),
        Index(
            "scratchpad_row_claim_idx",
            "scratchpad_id",
            "status",
            sql_text("priority DESC"),
            sql_text("row_id ASC"),
        ),
        Index("scratchpad_row_status_age_idx", "status", "status_updated_at"),
    )

    scratchpad_id: Mapped[str] = mapped_column(
        ForeignKey("scratchpad.id", ondelete="CASCADE"), primary_key=True
    )
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(nullable=False)
    text_hash: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=sql_text("'pending'"))
    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sql_text("0")
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))
    result: Mapped[str | None]
    error_reason: Mapped[str | None]
