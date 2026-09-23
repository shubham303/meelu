from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import (
    EMPTY_JSON_ARRAY,
    EMPTY_JSON_OBJECT,
    Base,
    EntityMixin,
    SiteScopedMixin,
)


class SocialListeningPost(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_post"
    __table_args__ = (
        UniqueConstraint("site_id", "url", name="social_listening_post_site_url_key"),
        Index("social_listening_post_site_idx", "site_id", "seq"),
        Index(
            "social_listening_post_pending_idx",
            "site_id",
            postgresql_where=text("embedding IS NULL"),
        ),
    )

    url: Mapped[str] = mapped_column(nullable=False)
    platform: Mapped[str] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str | None]
    text: Mapped[str | None]
    author_handle: Mapped[str | None]
    author_name: Mapped[str | None]
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    engagement: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT)
    matched_targets: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    intent: Mapped[str | None]
    sentiment: Mapped[str | None]
    is_question: Mapped[bool | None]
    classes: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    relevance: Mapped[float | None]
    composite_score: Mapped[float | None]
    keep_reason: Mapped[str | None]
    suggested_angle: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'fetched'"))
    similarity: Mapped[float | None]
    query_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_listening_query.id", ondelete="SET NULL")
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embed_model: Mapped[str | None]
    embed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    embed_error: Mapped[str | None]
    reply_text: Mapped[str | None]
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_listening_run.id", ondelete="SET NULL")
    )
