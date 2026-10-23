import asyncio

from src.providers.json_data_extractor.adapter import Question, boolean, said_yes
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.providers.social_search.models.social_post import SocialPost
from src.social_listening.models.post import SocialListeningPost

CHECK_BATCH = 20
CHECK_CONCURRENCY = 3
TEXT_CHARS = 600
FITS = "the post matches what the marketer wrote"
MISFITS = "the post does not match what the marketer wrote"
INSTRUCTIONS = (
    "Does this post match the conversation the marketer described? Judge only by what they "
    "wrote and add no rule of your own. Post: "
)
FALLBACK_LINE = "the conversations the marketer listens for"


def post_text(post: SocialPost) -> str:
    where = post.platform + (
        f" r/{post.context['subreddit']}" if (post.context or {}).get("subreddit") else ""
    )
    parts = [
        where,
        f"Title: {post.title}" if post.title else "",
        f"Text: {(post.text or '')[:TEXT_CHARS]}",
    ]
    return ". ".join(p for p in parts if p)


def questions(batch: list[tuple[SocialListeningPost, SocialPost]]) -> dict[str, Question]:
    return {
        f"p{seat}": boolean(INSTRUCTIONS + post_text(post), FITS, MISFITS)
        for seat, (_, post) in enumerate(batch)
    }


async def classify_posts(
    user_id: str,
    site_id: str,
    rows: list[tuple[SocialListeningPost, SocialPost]],
    lines: dict[str, str],
) -> tuple[list[tuple[SocialListeningPost, bool]], list[str], int]:
    caller = Caller(user_id=user_id, site_id=site_id)
    gate = asyncio.Semaphore(CHECK_CONCURRENCY)
    errors: list[str] = []
    groups: dict[str, list[tuple[SocialListeningPost, SocialPost]]] = {}
    for row in rows:
        groups.setdefault(lines.get(row[0].query_id or "", FALLBACK_LINE), []).append(row)
    planned = [
        (line, own[start : start + CHECK_BATCH])
        for line, own in groups.items()
        for start in range(0, len(own), CHECK_BATCH)
    ]

    async def decide(line: str, batch: list[tuple[SocialListeningPost, SocialPost]]):
        try:
            async with gate:
                result = await json_data_extractor.classify(
                    caller,
                    {"task": "social_listening_check", "line": line},
                    {"marketer_wrote": line},
                    questions(batch),
                )
        except Exception as exc:
            errors.append(str(exc))
            return []
        answers = result["answers"]
        return [
            (own, said_yes(answers[f"p{seat}"]))
            for seat, (own, _) in enumerate(batch)
            if f"p{seat}" in answers
        ]

    verdicts = [
        v for done in await asyncio.gather(*(decide(line, b) for line, b in planned)) for v in done
    ]
    return verdicts, errors, len(planned)
