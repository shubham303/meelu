from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class SeoKeywordClusterCompetitor(Base):
    __tablename__ = "seo_keyword_cluster_competitors"

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey("seo_keyword_clusters.id", ondelete="CASCADE"), primary_key=True
    )
    competitor_id: Mapped[str] = mapped_column(
        ForeignKey("seo_competitors.id", ondelete="CASCADE"), primary_key=True, index=True
    )
