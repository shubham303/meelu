from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class Conversation(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("conversations_prospect_idx", "prospect_id", "created_at"),
        Index("conversations_user_idx", "user_id", "created_at"),
        Index(
            "conversations_message_idx",
            "user_id",
            "message_id",
            unique=True,
            postgresql_where=text("message_id is not null"),
        ),
    )

    prospect_id: Mapped[str] = mapped_column(
        ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'draft'"))
    from_: Mapped[str | None] = mapped_column("from")
    to: Mapped[str | None]
    cc: Mapped[str | None]
    bcc: Mapped[str | None]
    subject: Mapped[str] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(nullable=False)
    message_id: Mapped[str | None]
    thread_ref: Mapped[str | None]
