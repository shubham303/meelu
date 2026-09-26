from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class SeoPageSuggestionKeyword(Base):
    __tablename__ = "seo_page_suggestion_keywords"

    suggestion_id: Mapped[str] = mapped_column(
        ForeignKey("seo_page_suggestions.id", ondelete="CASCADE"), primary_key=True
    )
    keyword_id: Mapped[str] = mapped_column(
        ForeignKey("seo_keywords.id", ondelete="CASCADE"), primary_key=True
    )
