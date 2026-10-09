from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_OBJECT, Base, EntityMixin, SiteScopedMixin


class SocialListeningPost(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_post"
    __table_args__ = (
        UniqueConstraint("site_id", "post_key", name="social_listening_post_site_key_key"),
        Index("social_listening_post_site_idx", "site_id", "seq"),
        Index("social_listening_post_site_status_idx", "site_id", "status"),
        Index("social_listening_post_content_hash_idx", "site_id", "content_hash"),
        Index(
            "social_listening_post_pending_idx",
            "site_id",
            postgresql_where=text("embedding IS NULL"),
        ),
    )

    post_key: Mapped[str] = mapped_column(nullable=False)
    external_id: Mapped[str | None]
    content_hash: Mapped[str | None]
    url: Mapped[str] = mapped_column(nullable=False)
    platform: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str | None]
    text: Mapped[str | None]
    author_handle: Mapped[str | None]
    author_name: Mapped[str | None]
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    engagement: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'fetched'"))
    drop_reason: Mapped[str | None]
    similarity: Mapped[float | None]
    relevance: Mapped[float | None]
    composite_score: Mapped[float | None]
    keep_reason: Mapped[str | None]
    suggested_angle: Mapped[str | None]
    reply_text: Mapped[str | None]
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    query_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_listening_query.id", ondelete="SET NULL")
    )
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_listening_run.id", ondelete="SET NULL")
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embed_model: Mapped[str | None]
    embed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    embed_error: Mapped[str | None]
