from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, TimestampedMixin


class AnalyticsChatMessage(TimestampedMixin, Base):
    __tablename__ = "analytics_chat_messages"
    __table_args__ = (Index("analytics_chat_messages_chat_idx", "chat_id", "seq"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    chat_id: Mapped[str] = mapped_column(
        ForeignKey("analytics_chats.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)
