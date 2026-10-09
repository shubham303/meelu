from typing import Any

from src.site_pages.schemas import SitePageLinkRecord
from src.site_structure.links import screening
from src.site_structure.links.schemas import ScreeningInput
from src.site_structure.pipeline.review import VERDICTS

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": [v.value for v in VERDICTS]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You review one proposed internal link on a website and decide whether it should be shown to the site owner.

The owner's brief for this run:
{prompt}

Answer with a verdict: "review_approved" when the link is worth the owner's time as the brief describes, "review_rejected" when it is not. Judge from the source passage, the target page and the suggestion text. Both pages carry details an earlier model extracted about them, such as their role and kind; read those details too before deciding. A link is not worth it when the pages are unrelated, when the passage does not really discuss what the target is about, when the passage is boilerplate, or when the link would read as spam to a reader.

Read the source passage itself, then the source page's existing links, listed with their anchor and the region they sit in (body, nav, footer and so on). Judge the new link against what those links already give the reader, not only against their URLs. For a new link, reject it when:
- the page already links to the target;
- the page already links to another page that covers the same thing along the same line, so the new link adds nothing a reader cannot already reach from this page;
- the body already links to so many pages that one more would crowd the reader.
For a removal, weigh which body links the page keeps and whether they cover what the removed link gave the reader. Give a one-sentence reason."""


def item_state(item: ScreeningInput, outbound: list[SitePageLinkRecord]) -> dict[str, Any]:
    state = screening.item_state(item)
    state["source"]["links"] = [
        {"url": link.dst_url, "anchor": link.anchor or "", "region": link.region}
        for link in outbound
    ]
    return state
