from typing import Any

from src.providers.json_data_extractor.adapter import Question, choice
from src.site_structure.constants import PillarAction
from src.site_structure.pillars.schemas import PillarReviewInput

ASK = {
    PillarAction.CREATE: "Do these pages form one coherent topic that deserves a single hub page introducing and linking all of them?",
    PillarAction.EXPAND: "Should the existing page be expanded into the hub that introduces and links all of these pages?",
}


def questions(action: PillarAction) -> dict[str, Question]:
    return {
        "apply": choice(
            f"{ASK[action]} Judge from the page titles, descriptions and URLs. Say yes only "
            "when a reader would expect one page to cover the whole set.",
            {
                "yes": "the pages share one clear topic and a hub page for them would help a reader",
                "no": "the pages are a loose mix, the topic is too broad or too thin, or a hub already covers them",
            },
        )
    }


def item_state(item: PillarReviewInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "topic": item.topic,
        "covering_page": {"url": item.covering_url or "", "title": item.covering_title or ""},
        "pages": [
            {"url": m["url"], "title": m["title"], "meta_description": m["meta_description"]}
            for m in item.members
        ],
    }
