from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, Integer, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class SocialListeningQuery(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "social_listening_query"
    __table_args__ = (
        UniqueConstraint("site_id", "text", name="social_listening_query_site_text_key"),
        Index("social_listening_query_site_idx", "site_id", "seq"),
    )

    text: Mapped[str] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, server_default=sql_text("true"))
    source: Mapped[str] = mapped_column(nullable=False, server_default=sql_text("'user'"))
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embed_model: Mapped[str | None]
    embed_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sql_text("0")
    )
    embed_error: Mapped[str | None]
