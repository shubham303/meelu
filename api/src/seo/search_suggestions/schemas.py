from pydantic import Field, field_validator

from src.core.schemas import EntityModel, RequestModel
from src.seo.keyword_clusters.schemas import normalize_keyword
from src.seo.search_suggestions.constants import MAX_SUGGESTION_KEYWORDS


class SearchSuggestionsRequest(RequestModel):
    keywords: list[str] = Field(min_length=1)
    use_cache: bool = False
    location_code: int | None = None

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, value: list[str]) -> list[str]:
        cleaned = [k for k in dict.fromkeys(normalize_keyword(v) for v in value) if k]
        if not cleaned:
            raise ValueError("Pass at least one keyword.")
        if len(cleaned) > MAX_SUGGESTION_KEYWORDS:
            raise ValueError(f"At most {MAX_SUGGESTION_KEYWORDS} keywords per call.")
        return cleaned


class PeopleAlsoAsk(EntityModel):
    question: str
    url: str | None = None


class SearchSuggestions(EntityModel):
    keyword: str
    location_code: int
    language_code: str
    autocomplete: list[str]
    people_also_ask: list[PeopleAlsoAsk]
    related_searches: list[str]
