from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoKeyword(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_keywords"
    __table_args__ = (
        UniqueConstraint("site_id", "keyword", name="seo_keywords_site_keyword_key"),
        Index("seo_keywords_cluster_idx", "site_id", "cluster_id"),
        Index("seo_keywords_branded_idx", "site_id", "branded"),
        Index(
            "seo_keywords_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "seo_keywords_pending_idx",
            "site_id",
            postgresql_where=text("embedding IS NULL"),
        ),
    )

    keyword: Mapped[str] = mapped_column(nullable=False)
    volume: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[int | None] = mapped_column(Integer)
    cpc: Mapped[float | None]
    intent: Mapped[str | None]
    facts_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_source: Mapped[str] = mapped_column(nullable=False)
    seed_keyword_id: Mapped[str | None] = mapped_column(
        ForeignKey("seo_keywords.id", ondelete="SET NULL")
    )
    cluster_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "seo_keyword_clusters.id",
            ondelete="SET NULL",
            use_alter=True,
            name="seo_keywords_cluster_id_fkey",
        )
    )
    branded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    our_position: Mapped[int | None] = mapped_column(Integer)
    our_url: Mapped[str | None]
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embed_model: Mapped[str | None]
    embed_error: Mapped[str | None]
    impressions_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    clicks_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions_prev_28d: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    clicks_prev_28d: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    impressions_ly_28d: Mapped[int | None] = mapped_column(Integer)
    clicks_ly_28d: Mapped[int | None] = mapped_column(Integer)


class SeoKeywordCluster(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_keyword_clusters"
    __table_args__ = (Index("seo_keyword_clusters_site_idx", "site_id"),)

    head_keyword_id: Mapped[str] = mapped_column(
        ForeignKey(
            "seo_keywords.id",
            ondelete="CASCADE",
            use_alter=True,
            name="seo_keyword_clusters_head_keyword_id_fkey",
        ),
        nullable=False,
    )
    centroid: Mapped[list[float] | None] = mapped_column(Vector(384))
    size: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    volume_sum: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    difficulty_median: Mapped[float | None]
    owner_page_id: Mapped[str | None]
    owner_coverage: Mapped[float | None]
    site_similarity: Mapped[float | None]
    rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
