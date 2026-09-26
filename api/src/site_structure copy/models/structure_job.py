from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class StructureJob(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "structure_jobs"
    __table_args__ = (Index("structure_jobs_site_idx", "site_id", "status"),)

    prompt: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'RUNNING'"))
