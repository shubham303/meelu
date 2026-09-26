from sqlalchemy import BigInteger, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SeoJob(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_jobs"
    __table_args__ = (Index("seo_jobs_site_idx", "site_id", "status"),)

    prompt: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'RUNNING'"))
    vendor_calls: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    vendor_micros: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    vendor_ceiling_micros: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
