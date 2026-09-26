from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoKeywordContentPage(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_keyword_content_pages"
    __table_args__ = (
        UniqueConstraint("keyword_id", "page_id", name="seo_keyword_content_pages_pair_key"),
        Index("seo_keyword_content_pages_page_idx", "site_id", "page_id"),
        Index("seo_keyword_content_pages_keyword_idx", "site_id", "keyword_id"),
    )

    keyword_id: Mapped[str] = mapped_column(
        ForeignKey("seo_keywords.id", ondelete="CASCADE"), nullable=False
    )
    page_id: Mapped[str] = mapped_column(nullable=False)
    coverage: Mapped[float] = mapped_column(nullable=False)
    lexical_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
