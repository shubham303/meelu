from typing import Any

from src.site_structure.review import VERDICTS
from src.site_structure.schemas import PillarReviewInput

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
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

Answer with a verdict: "ready" when the pages form one topic a reader would expect a single page to cover and the site has no such page, "llm_rejected" when they are a loose mix, the topic is too broad or too thin, or an existing page already does the job. When the action is "expand", judge whether the named existing page should grow into that hub.

When the verdict is ready, write the title the pillar page should carry and a suggestion the owner can act on: what the page must cover, which of the listed pages it should link to and in what order, and which of them should link back. Otherwise leave title and suggestion empty. Give a one-sentence reason."""


def review_state(item: PillarReviewInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "topic": item.topic,
        "cohesion": item.search_score,
        "covering_page": {"url": item.covering_url or "", "title": item.covering_title or ""},
        "pages": item.members,
    }
