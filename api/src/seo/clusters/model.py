from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


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
