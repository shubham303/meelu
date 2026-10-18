from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, DateTime, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_OBJECT, Base, TimestampedMixin


class SocialPost(TimestampedMixin, Base):
    __tablename__ = "social_post"
    __table_args__ = (
        Index("social_post_platform_fetched_idx", "platform", "fetched_at"),
        Index("social_post_search_idx", "search", postgresql_using="gin"),
        Index(
            "social_post_pending_embed_idx",
            "seq",
            postgresql_where=text("embedding IS NULL"),
        ),
        Index("social_post_posted_idx", "posted_at"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    post_key: Mapped[str] = mapped_column(nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    external_id: Mapped[str | None]
    title: Mapped[str | None]
    text: Mapped[str | None]
    author_handle: Mapped[str | None]
    author_name: Mapped[str | None]
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    engagement: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT)
    content_hash: Mapped[str | None]
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    search: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(text, ''))",
            persisted=True,
        ),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embed_model: Mapped[str | None]
    embed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    embed_error: Mapped[str | None]
