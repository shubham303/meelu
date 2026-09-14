from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class Note(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "notes"
    __table_args__ = (
        Index("notes_site_idx", "site_id"),
        Index(
            "notes_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "notes_pending_idx",
            "site_id",
            postgresql_where=text("embedding IS NULL"),
        ),
    )

    note: Mapped[str] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(nullable=False, server_default=text("'note'"))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embed_model: Mapped[str | None]
