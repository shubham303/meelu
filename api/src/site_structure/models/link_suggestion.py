from sqlalchemy import REAL, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class LinkSuggestion(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "link_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "from_page_id",
            "from_chunk_id",
            "to_page_id",
            "action",
            name="link_suggestions_edge_idx",
            postgresql_nulls_not_distinct=True,
        ),
        Index("link_suggestions_job_idx", "job_id"),
        Index("link_suggestions_state_idx", "site_id", "state"),
        Index("link_suggestions_from_idx", "site_id", "from_page_id"),
        Index("link_suggestions_to_idx", "site_id", "to_page_id"),
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("structure_jobs.id", ondelete="CASCADE"), nullable=False
    )
    from_page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    from_chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey("site_chunks.id", ondelete="CASCADE")
    )
    to_page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(nullable=False, server_default=text("'create'"))
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'draft'"))
    suggestion: Mapped[str] = mapped_column(nullable=False)
    search_score: Mapped[float | None] = mapped_column(REAL)  # higher the better
    confidence: Mapped[float | None] = mapped_column(REAL)  # higher the better
    score: Mapped[float | None] = mapped_column(REAL)
