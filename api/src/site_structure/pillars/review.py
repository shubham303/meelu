from typing import Any

from src.site_structure.pillars.schemas import PillarReviewInput
from src.site_structure.pipeline.review import VERDICTS

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": [v.value for v in VERDICTS]},
        "title": {"type": "string"},
        "suggestion": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "title", "suggestion", "reason"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You review one proposed pillar page for a website: a hub that introduces a topic and links to every page the site already has on it. Decide whether the owner should build it.

The owner's brief for this run:
{prompt}

Answer with a verdict: "review_approved" when the pages form one topic a reader would expect a single page to cover and the site has no such page, "review_rejected" when they are a loose mix, the topic is too broad or too thin, or an existing page already does the job. When the action is "expand", judge whether the named existing page should grow into that hub. Every page, the covering page included, carries details an earlier model extracted about it, such as its role and kind; read those details too before deciding.

When the verdict is review_approved, write the title the pillar page should carry and a suggestion the owner can act on: what the page must cover, which of the listed pages it should link to and in what order, and which of them should link back. Otherwise leave title and suggestion empty. Give a one-sentence reason."""


def item_state(item: PillarReviewInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "topic": item.topic,
        "cohesion": item.search_score,
        "covering_page": {
            "url": item.covering_url or "",
            "title": item.covering_title or "",
            "details": item.covering_details or "",
        },
        "pages": item.members,
    }
