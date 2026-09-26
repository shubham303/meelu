from typing import Any

from src.site_structure.schemas import ScreeningInput

VERDICTS = ("ready", "llm_rejected")

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You review one proposed internal link on a website and decide whether it should be shown to the site owner.

The owner's brief for this run:
{prompt}

Answer with a verdict: "ready" when the link is worth the owner's time as the brief describes, "llm_rejected" when it is not. Judge from the source passage, the target page and the suggestion text. A link is not worth it when the pages are unrelated, when the passage does not really discuss what the target is about, when the passage is boilerplate, or when the link would read as spam to a reader. Give a one-sentence reason."""


def review_state(item: ScreeningInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "suggestion": item.suggestion,
        "source": {
            "url": item.from_url,
            "title": item.from_title or "",
            "text": item.from_text,
            "anchor": item.anchor or "",
        },
        "target": {
            "url": item.to_url,
            "title": item.to_title or "",
            "meta_description": item.to_meta_description or "",
            "h1": item.to_h1,
            "page_type": item.to_page_type or "",
        },
    }
