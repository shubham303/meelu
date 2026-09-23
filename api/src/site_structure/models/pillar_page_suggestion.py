from sqlalchemy import REAL, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class PillarPageSuggestion(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "pillar_page_suggestions"
    __table_args__ = (
        Index("pillar_page_suggestions_job_idx", "job_id"),
        Index("pillar_page_suggestions_state_idx", "site_id", "state"),
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("structure_jobs.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(nullable=False, server_default=text("'create'"))
    topic: Mapped[str] = mapped_column(nullable=False)
    member_page_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'")
    )
    covering_page_id: Mapped[str | None] = mapped_column(
        ForeignKey("site_pages.id", ondelete="SET NULL")
    )
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'draft'"))
    suggestion: Mapped[str] = mapped_column(nullable=False)
    search_score: Mapped[float | None] = mapped_column(REAL)
    confidence: Mapped[float | None] = mapped_column(REAL)
    score: Mapped[float | None] = mapped_column(REAL)
