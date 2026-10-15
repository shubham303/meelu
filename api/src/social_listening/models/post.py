from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SocialListeningPost(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_post"
    __table_args__ = (
        UniqueConstraint("site_id", "post_id", name="social_listening_post_site_post_key"),
        Index("social_listening_post_site_status_idx", "site_id", "status"),
        Index("social_listening_post_post_idx", "post_id"),
    )

    post_id: Mapped[str] = mapped_column(
        ForeignKey("social_post.id", ondelete="CASCADE"), nullable=False
    )
    query_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_listening_query.id", ondelete="SET NULL")
    )
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_listening_run.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'candidate'"))
    similarity: Mapped[float | None]
    keep_reason: Mapped[str | None]
    suggested_angle: Mapped[str | None]
    reply_text: Mapped[str | None]
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
