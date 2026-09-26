from src.core.schemas import EntityModel
from src.seo.page_suggestions.schemas import PageSuggestionSummary
from src.seo.state.schemas import SiteStateRecord


class OverviewResponse(EntityModel):
    keywords: int
    keywords_with_facts: int
    clusters: int
    competitors_confirmed: int
    suggestions: PageSuggestionSummary
    state: SiteStateRecord
