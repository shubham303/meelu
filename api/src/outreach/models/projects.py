from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class Project(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (Index("projects_user_idx", "user_id", "created_at"),)

    name: Mapped[str] = mapped_column(nullable=False)
    goal: Mapped[str | None]
    prompt: Mapped[str | None]
    prospect_profile: Mapped[str] = mapped_column(nullable=False)
    search_criteria: Mapped[str | None]
    email_tone: Mapped[str | None]
    value_prop: Mapped[str | None]
    cta: Mapped[str | None]
