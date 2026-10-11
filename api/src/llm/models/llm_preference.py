from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class LlmPreference(Base):
    __tablename__ = "llm_preference"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    default_model: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
