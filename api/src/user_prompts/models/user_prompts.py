from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class UserPrompt(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "user_prompts"
    __table_args__ = (
        UniqueConstraint("site_id", "surface", "label", name="user_prompts_label_key"),
        Index("user_prompts_site_surface_idx", "site_id", "surface"),
    )

    surface: Mapped[str] = mapped_column(nullable=False)
    label: Mapped[str] = mapped_column(nullable=False)
    prompt: Mapped[str] = mapped_column(nullable=False)
