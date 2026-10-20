from typing import Any

from src.geo.schemas import INTENTS, POINT_STATUSES

UNDERSTAND = """The data holds one question a person typed into an AI assistant or a search engine.
Decide its search intent: informational (wants to learn or do something), commercial (is comparing options before buying), transactional (wants to buy, sign up or download now) or navigational (wants one specific site or page).
Then list the points a complete answer must contain for THIS exact question. Be meticulous: keep every constraint the question carries (a price, a place, a version, an audience, a comparison, "step by step", "for X"). Each point is a short phrase naming one thing the reader needs, not a topic. Two to six points. Do not add points the question does not ask for."""

UNDERSTAND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": list(INTENTS)},
        "points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["intent", "points"],
    "additionalProperties": False,
}

JUDGE_PAGE = """The data holds a question, its intent, the points a complete answer must contain, and the full text of one web page.
For each point, decide whether the page gives the reader what that point asks for:
- answers: the page states it plainly enough that a reader needs nothing else for this point.
- partly: the page touches it but leaves the reader short (too vague, only the definition when steps were asked, missing the constraint).
- missing: the page does not give it. A page on the same topic that does not answer this point is missing, not partly.
Judge the exact point, not the topic. For answers and partly, quote the shortest passage of the page that shows it as evidence; for missing, leave evidence empty. Return the points in the order given, with their text unchanged."""

JUDGE_PAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "point": {"type": "string"},
                    "status": {"type": "string", "enum": list(POINT_STATUSES)},
                    "evidence": {"type": "string"},
                },
                "required": ["point", "status", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["points"],
    "additionalProperties": False,
}

COMPARE = """The data holds a question, its intent, the points a complete answer must contain, the site's best page for it (full text, or null when the site has none), that page's average Google position, the verdict already reached, the advice that goes with that verdict, and the answers AI systems gave to the same question.
1. For each AI answer, list which of the required points it covers and which it misses, using the point text as given.
2. List what the site's page offers that none of the AI answers give: first-hand data, specifics, steps, prices, examples, a tool. Only things the page text actually contains. Empty when there is no page or it adds nothing.
3. Write the suggestion: two to four plain sentences for the site owner, following the advice for the verdict and grounded in this question, these AI answers and this page. Name the missing points or what the page adds where it helps. The owner decides and makes every change; suggest, never claim anything was changed, and never promise a citation, since AI answers differ from run to run."""

COMPARE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "covers": {"type": "array", "items": {"type": "string"}},
                    "misses": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["platform", "covers", "misses"],
                "additionalProperties": False,
            },
        },
        "pageAdds": {"type": "array", "items": {"type": "string"}},
        "suggestion": {"type": "string"},
    },
    "required": ["answers", "pageAdds", "suggestion"],
    "additionalProperties": False,
}

ADVICE = {
    "no_page": "No page on the site answers this question. Suggest a new page that answers every required point, and say what the AI answers cover and miss so the page can do better. The Content desk can write it.",
    "partial": "A page comes close but leaves required points short or missing. Name those points and suggest extending the page with them; leaving the page as it is stays the owner's call.",
    "low_rank": "The page answers the question fully, but it ranks poorly or not at all in Google, so AI search rarely finds it. Suggest improving its SEO, submitting the site to Bing Webmaster Tools (with IndexNow) and Brave Search, since ChatGPT search leans on Bing and Claude on Brave, and checking that robots.txt lets the AI search bots in (OAI-SearchBot, Claude-SearchBot, PerplexityBot).",
    "covered": "The page answers the question and ranks on Google's first page. Say it is covered, mention what it adds over the AI answers, and note that AI answers change from run to run, so a citation is never guaranteed and a re-check later is worthwhile.",
}
