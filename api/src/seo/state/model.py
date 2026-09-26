from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_OBJECT, EMPTY_TEXT_ARRAY, Base, EntityMixin, SiteScopedMixin


class SeoSiteState(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "seo_site_state"
    __table_args__ = (Index("seo_site_state_site_idx", "site_id", unique=True),)

    location_code: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("2840"))
    language_code: Mapped[str] = mapped_column(nullable=False, server_default=text("'en'"))
    brand_terms: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT), nullable=False, server_default=EMPTY_TEXT_ARRAY
    )
    precompute_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rollup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ctr_curve: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT
    )
