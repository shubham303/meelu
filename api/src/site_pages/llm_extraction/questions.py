from typing import Any

from src.providers.json_data_extractor.adapter import Question, choice
from src.site_pages.schemas.llm_extraction import (
    BROAD_PAGE_TYPE_GUIDE,
    BROAD_PAGE_TYPES,
    PAGE_TYPE_GUIDE,
    PAGE_TYPES,
)

MAX_BODY_CHARS = 8000
MIN_CONFIDENCE = 0.7
REVIEWED_CONFIDENCE = 1.0


QUESTIONS: dict[str, Question] = {
    "page_type": choice(
        "What is this web page for? Decide from what the page is for, not from how it is worded. "
        "When a page mixes roles, pick the one the owner most wants a visitor to act on.",
        {t: PAGE_TYPE_GUIDE[t] for t in PAGE_TYPES},
    ),
    "broad_page_type": choice(
        "What kind of page is this? Decide from what the page offers or does, not from how it "
        "is worded. A product is something the visitor buys, a service is work the business does "
        "for its clients, and a feature is one capability of the owner's software.",
        {t: BROAD_PAGE_TYPE_GUIDE[t] for t in BROAD_PAGE_TYPES},
    ),
}


def page_state(
    url: str, title: str | None, h1: list[str], meta_description: str | None, body: str | None
) -> dict:
    return {
        "url": url,
        "title": title or "",
        "h1": h1,
        "meta_description": meta_description or "",
        "body_text": (body or "")[:MAX_BODY_CHARS],
    }


def _settled(answer: dict[str, Any] | None) -> tuple[str | None, float | None]:
    if answer is None:
        return None, None
    confidence = answer.get("confidence")
    settled = confidence is not None and confidence >= MIN_CONFIDENCE
    return (answer["choice"] if settled else None), confidence


def read_answers(answers: dict[str, Any]) -> dict[str, Any]:
    page_type, confidence = _settled(answers["page_type"])
    broad_page_type, broad_confidence = _settled(answers.get("broad_page_type"))
    return {
        "page_type": page_type,
        "confidence": confidence,
        "broad_page_type": broad_page_type,
        "broad_page_type_confidence": broad_confidence,
        "use_large_llm_review": page_type is None or broad_page_type is None,
    }


def invalid_review_answers(answers: dict[str, str]) -> list[str]:
    return [
        key for key, question in QUESTIONS.items() if answers.get(key) not in question["criteria"]
    ]


def read_review_answers(answers: dict[str, str]) -> dict[str, Any]:
    return {
        "page_type": answers["page_type"],
        "confidence": REVIEWED_CONFIDENCE,
        "broad_page_type": answers["broad_page_type"],
        "broad_page_type_confidence": REVIEWED_CONFIDENCE,
        "use_large_llm_review": False,
    }
