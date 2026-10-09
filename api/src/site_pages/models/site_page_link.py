from sqlalchemy import Boolean, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SitePageLink(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_page_links"
    __table_args__ = (
        Index(
            "site_page_links_edge_idx",
            "site_id",
            "src_page_id",
            "dst_url",
            "region",
            unique=True,
        ),
        Index("site_page_links_dst_idx", "site_id", "dst_page_id"),
        Index("site_page_links_src_idx", "site_id", "src_page_id"),
        Index("site_page_links_dst_url_idx", "site_id", "dst_url"),
    )

    src_page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    dst_page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    dst_url: Mapped[str] = mapped_column(nullable=False)
    region: Mapped[str] = mapped_column(nullable=False, server_default=text("'body'"))
    rel: Mapped[str | None]
    anchor: Mapped[str | None]
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    followable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    dst_canonical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
