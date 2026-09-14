from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SiteChunk(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_chunks"
    __table_args__ = (
        Index("site_chunks_page_ordinal_idx", "page_id", "ordinal", unique=True),
        Index("site_chunks_site_idx", "site_id"),
        Index(
            "site_chunks_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "site_chunks_pending_idx",
            "site_id",
            postgresql_where=sql_text("embedding IS NULL"),
        ),
    )

    page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[str | None]
    text: Mapped[str] = mapped_column(nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embed_model: Mapped[str | None]
    embedded_from_hash: Mapped[str | None]
    embed_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sql_text("0")
    )
    embed_error: Mapped[str | None]
    chunk_strategy: Mapped[str | None]
    from_hash: Mapped[str | None]
