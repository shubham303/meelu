from sqlalchemy import Computed, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, TimestampedMixin


class AgentPlan(TimestampedMixin, Base):
    __tablename__ = "agent_plans"
    __table_args__ = (
        Index("agent_plans_tsv_idx", "tsv", postgresql_using="gin"),
        Index(
            "agent_plans_builtin_slug_idx",
            "slug",
            unique=True,
            postgresql_where=text("user_id IS NULL"),
        ),
        Index("agent_plans_user_slug_idx", "user_id", "slug", unique=True),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(nullable=False)
    question: Mapped[str] = mapped_column(nullable=False)
    plan: Mapped[str] = mapped_column(nullable=False)
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', question), 'A') || "
            "setweight(to_tsvector('english', plan), 'B')",
            persisted=True,
        ),
    )
