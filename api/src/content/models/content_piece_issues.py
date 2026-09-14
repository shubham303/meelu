from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class ContentPieceIssue(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "content_piece_issues"
    __table_args__ = (Index("content_piece_issues_piece_idx", "piece_id", "state"),)

    piece_id: Mapped[str] = mapped_column(
        ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
    )
    tool: Mapped[str] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    detail: Mapped[str | None]
    anchor_text: Mapped[str | None]
    suggestion: Mapped[str | None]
    state: Mapped[str] = mapped_column(nullable=False, server_default=text("'open'"))
    run_id: Mapped[str] = mapped_column(nullable=False)
