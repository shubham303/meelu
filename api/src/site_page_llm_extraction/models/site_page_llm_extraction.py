from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SitePageLlmExtraction(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_page_llm_extraction"
    __table_args__ = (
        Index("site_page_llm_extraction_page_idx", "page_id", unique=True),
        Index("site_page_llm_extraction_site_idx", "site_id"),
    )

    page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    page_type: Mapped[str | None]
    confidence: Mapped[float | None] = mapped_column(Float)
    extracted_from_hash: Mapped[str | None]
    model: Mapped[str | None]
    error: Mapped[str | None]
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
