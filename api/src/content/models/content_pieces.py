from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class ContentPiece(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "content_pieces"
    __table_args__ = (
        Index("content_pieces_user_idx", "user_id", "created_at"),
        Index("content_pieces_site_status_idx", "site_id", "status"),
        Index("content_pieces_slot_idx", "site_id", "channel_key", "scheduled_at"),
        Index("content_pieces_parent_idx", "parent_piece_id"),
    )

    title: Mapped[str] = mapped_column(nullable=False)
    body_markdown: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    channel_key: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'draft'"))
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    checks: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_url: Mapped[str | None]
    external_post_id: Mapped[str | None]
    failure: Mapped[str | None]
    created_by: Mapped[str] = mapped_column(nullable=False, server_default=text("'user'"))
    media_source: Mapped[str] = mapped_column(nullable=False, server_default=text("'none'"))
    media_url: Mapped[str | None]
    media_alt: Mapped[str | None]
    media_width: Mapped[int | None] = mapped_column(Integer)
    media_height: Mapped[int | None] = mapped_column(Integer)
    media_credit_name: Mapped[str | None]
    media_credit_url: Mapped[str | None]
    media_upload_id: Mapped[str | None] = mapped_column(
        ForeignKey("post_media.id", ondelete="SET NULL")
    )
    source_page_id: Mapped[str | None] = mapped_column(
        ForeignKey("site_pages.id", ondelete="SET NULL")
    )
    parent_piece_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_pieces.id", ondelete="SET NULL")
    )
