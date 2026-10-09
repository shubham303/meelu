from typing import Any

from src.providers.json_data_extractor.adapter import Question, choice
from src.site_structure.links.schemas import LinkAction, ScreeningInput

DEFAULT_ASK = {
    LinkAction.CREATE: "Should the source passage gain a link to the target page?",
    LinkAction.DELETE: "Should the existing link from the source page to the target page be removed?",
}


def questions(action: LinkAction, question: str | None) -> dict[str, Question]:
    ask = question or DEFAULT_ASK[action]
    return {
        "apply": choice(
            f"{ask} Judge from the source text, the target page and the suggestion. "
            "Each page carries details an earlier model extracted about it, such as its role "
            "and kind; read those details too before deciding. "
            "Say yes only when a reader of the source would plausibly want the target next "
            "and the change fits how the page is written.",
            {
                "yes": "the change is worth making: the target is relevant to the source passage and the suggestion holds",
                "no": "the change is not worth making: the pages are unrelated, the suggestion is weak, or the link would read as spam",
            },
        )
    }


def item_state(item: ScreeningInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "suggestion": item.suggestion,
        "source": {
            "url": item.from_url,
            "title": item.from_title or "",
            "text": item.from_text,
            "anchor": item.anchor or "",
            "details": item.from_details,
        },
        "target": {
            "url": item.to_url,
            "title": item.to_title or "",
            "meta_description": item.to_meta_description or "",
            "h1": item.to_h1,
            "details": item.to_details,
        },
    }
