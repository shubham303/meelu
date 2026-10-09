from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.schemas import EntityModel, RequestModel

PAGE_TYPES = ("money", "hub", "informational", "support", "company", "legal", "utility")

PageType = Literal[PAGE_TYPES]

PAGE_TYPE_GUIDE = {
    "money": "anything the owner wants users to land on and act on: a product, service, tool, pricing, signup, booking or location page, and the home or landing page",
    "hub": "category, collection, blog index and topic overview pages whose job is to route users and link equity to other pages",
    "informational": "blog posts, guides, glossary entries, news and comparisons",
    "support": "FAQ, docs, help center, shipping and returns",
    "company": "about, team, careers, press, testimonials and contact",
    "legal": "privacy, terms, cookies, disclaimers",
    "utility": "login, cart, checkout, search results, facets, pagination, tag or author archives, thank-you pages",
}

BROAD_PAGE_TYPES = (
    "home",
    "product",
    "product_listing",
    "service",
    "feature",
    "solution",
    "integration",
    "pricing",
    "location",
    "lead_capture",
    "tool",
    "case_study",
    "comparison",
    "article",
    "guide",
    "glossary",
    "content_listing",
    "docs",
    "event",
    "about",
    "careers",
    "contact",
    "legal",
    "account",
    "utility",
    "other",
)

BroadPageType = Literal[BROAD_PAGE_TYPES]

BROAD_PAGE_TYPE_GUIDE = {
    "home": "the site's home page",
    "product": "sells one physical or digital product the visitor can buy, such as a product detail page",
    "product_listing": "lists many products for sale, such as a shop category or collection",
    "service": "describes a service the business performs for its clients, such as consulting, an agency service, a repair or a treatment",
    "feature": "describes one feature or capability of the owner's software or app",
    "solution": "pitches the offer to one industry, role or use case, such as 'for agencies' or 'for healthcare'",
    "integration": "describes how the product connects with another tool, app or platform",
    "pricing": "plans, prices and what each plan includes",
    "location": "a store, office, branch or service-area page for one place",
    "lead_capture": "exists to get a signup, demo request, booking, quote request, free trial or download",
    "tool": "a free interactive tool, calculator, generator or template",
    "case_study": "a customer story, portfolio item or project showcase",
    "comparison": "compares products or lists alternatives, such as 'X vs Y' or 'best X'",
    "article": "a blog post, news item or opinion piece",
    "guide": "a long how-to, tutorial or complete guide that teaches a topic",
    "glossary": "defines one term or concept",
    "content_listing": "lists articles, guides or other content, such as a blog index, category, tag or author page",
    "docs": "product documentation, help center articles or FAQ",
    "event": "a webinar, event, course session or recording",
    "about": "about the company, its team, mission or press",
    "careers": "jobs and hiring",
    "contact": "how to contact the business",
    "legal": "privacy, terms, cookies, disclaimers",
    "account": "login, account, cart or checkout",
    "utility": "search results, pagination, thank-you pages or other pages with no content of their own",
    "other": "none of the above fits",
}

NO_EXTRACTED_DETAILS = "Nothing has been extracted from this page yet."


def extracted_details(record: "PageLlmExtractionRecord | None") -> str:
    return NO_EXTRACTED_DETAILS if record is None else str(record)


EXTRACTED_FIELDS = (
    (
        "page_type",
        "confidence",
        "Page role: what the page is for on the site",
        PAGE_TYPE_GUIDE,
    ),
    (
        "broad_page_type",
        "broad_page_type_confidence",
        "Page kind: what the page offers or does",
        BROAD_PAGE_TYPE_GUIDE,
    ),
)


class PageLlmExtractionFields(RequestModel):
    page_type: PageType | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    broad_page_type: BroadPageType | None = None
    broad_page_type_confidence: float | None = Field(default=None, ge=0, le=1)


class PageLlmExtractionCreateRequest(PageLlmExtractionFields):
    page_id: str
    extracted_from_hash: str | None = None
    model: str | None = None
    error: str | None = None
    use_large_llm_review: bool = False

    def values(self) -> dict[str, Any]:
        return self.model_dump(exclude={"page_id"})


class PageLlmExtractionPageTypeRequest(RequestModel):
    page_type: PageType


class PageLlmExtractionReviewRequest(RequestModel):
    content_hash: str
    model: str = Field(min_length=1)
    answers: dict[str, str]


class PageLlmExtractionReviewQueueQuery(RequestModel):
    limit: int = Field(default=20, ge=1, le=100)


class PageLlmExtractionListQuery(RequestModel):
    page_type: PageType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    def paging(self) -> PaginationParams:
        return PaginationParams(page=self.page, page_size=self.page_size).validate()


class PageLlmExtractionRecord(EntityModel):
    id: str
    site_id: str
    page_id: str
    page_type: str | None
    confidence: float | None
    broad_page_type: str | None
    broad_page_type_confidence: float | None
    extracted_from_hash: str | None
    model: str | None
    error: str | None
    use_large_llm_review: bool
    extracted_at: datetime
    created_at: datetime
    updated_at: datetime

    def __str__(self) -> str:
        lines = []
        for field, confidence_field, label, guide in EXTRACTED_FIELDS:
            value = getattr(self, field)
            confidence = getattr(self, confidence_field)
            sure = "" if confidence is None else f" (model confidence {confidence:.2f})"
            if value is None:
                lines.append(f"{label}: not settled{sure}.")
            else:
                lines.append(f"{label}: {value}, meaning {guide.get(value, value)}{sure}.")
        return "\n".join(lines)


class PendingPageRecord(EntityModel):
    id: str
    url: str
    title: str | None
    h1: list[str]
    meta_description: str | None
    content_hash: str | None
    body_text: str | None


class ReviewPageRecord(EntityModel):
    page_id: str
    url: str
    title: str | None
    h1: list[str]
    meta_description: str | None
    content_hash: str
    body_text: str


class ReviewQueueRecord(EntityModel):
    questions: dict[str, Any]
    pages: list[ReviewPageRecord]
    total: int


class ExtractionState(EntityModel):
    page_type: str | None
    extracted_from_hash: str | None
    error: str | None
    extract_attempts: int


class PageLlmExtractionStatsRecord(EntityModel):
    eligible: int
    extracted: int
    pending: int


class PageLlmExtractionResponse(PageLlmExtractionRecord):
    pass


class PageLlmExtractionListResponse(PaginatedApiResponse[PageLlmExtractionResponse]):
    pass


class PageLlmExtractionStatsResponse(EntityModel):
    stats: PageLlmExtractionStatsRecord


class PageLlmExtractionReviewQueueResponse(ReviewQueueRecord):
    pass


class PageLlmExtractionDeleteResponse(EntityModel):
    id: str
