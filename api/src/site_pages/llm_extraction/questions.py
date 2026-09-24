from typing import Any

from src.providers.json_data_extractor.adapter import Question, choice
from src.site_pages.schemas.llm_extraction import PAGE_TYPES

MAX_BODY_CHARS = 8000

PAGE_TYPE_GUIDE = {
    "money": "anything the owner wants users to land on and act on: a product, service, tool, pricing, signup, booking or location page, and the home or landing page",
    "hub": "category, collection, blog index and topic overview pages whose job is to route users and link equity to other pages",
    "informational": "blog posts, guides, glossary entries, news and comparisons",
    "support": "FAQ, docs, help center, shipping and returns",
    "company": "about, team, careers, press, testimonials and contact",
    "legal": "privacy, terms, cookies, disclaimers",
    "utility": "login, cart, checkout, search results, facets, pagination, tag or author archives, thank-you pages",
}

QUESTIONS: dict[str, Question] = {
    "page_type": choice(
        "What is this web page for? Decide from what the page is for, not from how it is worded. "
        "When a page mixes roles, pick the one the owner most wants a visitor to act on.",
        {t: PAGE_TYPE_GUIDE[t] for t in PAGE_TYPES},
    ),
}


def page_state(url: str, title: str | None, meta_description: str | None, body: str | None) -> dict:
    return {
        "url": url,
        "title": title or "",
        "meta_description": meta_description or "",
        "body_text": (body or "")[:MAX_BODY_CHARS],
    }


def read_answers(answers: dict[str, Any]) -> dict[str, Any]:
    page_type = answers["page_type"]
    return {"page_type": page_type["choice"], "confidence": page_type.get("confidence")}
