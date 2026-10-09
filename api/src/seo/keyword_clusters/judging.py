import asyncio
from typing import Any

from src.core.database import unit_of_work
from src.providers.json_data_extractor.adapter import Question, choice
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.seo.keyword_clusters.constants import INTENT_FIT, LLM_BATCH, LLM_CONCURRENCY

RELEVANT = {
    "yes": "a real search a potential customer of this website could make, about what the seeds and the website are about",
    "no": "noise or off-topic: gibberish, another company's brand or login, jobs or salaries, piracy, a different meaning of a shared word, or a subject the website does not cover",
}

SAME_RESULTS = {
    "yes": "the same need: Google would show largely the same pages for both searches",
    "no": "a different need, product, audience or format: Google would show different pages",
}

FITS = {
    "full": "the page is exactly what a person searching this wants, in the format they expect",
    "partial": "the page touches the need but is broader, narrower, a different format or a different audience",
    "none": "the page does not serve this search: a different meaning, a homepage, a login, an unrelated list",
}


def batches(items: list[Any]) -> list[list[Any]]:
    return [items[start : start + LLM_BATCH] for start in range(0, len(items), LLM_BATCH)]


async def ask(
    caller: Caller, subject: dict[str, Any], state: Any, questions: dict[str, Question]
) -> dict[str, Any]:
    async with unit_of_work() as db:
        result = await json_data_extractor.decide(db, caller, subject, state, questions)
    return result["answers"]


def chosen(answers: dict[str, Any], key: str) -> str | None:
    return (answers.get(key) or {}).get("choice")


async def relevant_keywords(
    caller: Caller, website: dict[str, Any], seeds: list[str], keywords: list[str]
) -> list[str]:
    gate = asyncio.Semaphore(LLM_CONCURRENCY)

    async def judge(batch: list[str]) -> list[str]:
        questions = {
            f"k{seat}": choice(
                f'Is "{keyword}" a search worth targeting for this website?', RELEVANT
            )
            for seat, keyword in enumerate(batch)
        }
        async with gate:
            answers = await ask(
                caller,
                {
                    "task": "keyword_relevance",
                    "website": website,
                    "seeds": seeds,
                    "keywords": batch,
                },
                {"website": website, "seed_keywords": seeds},
                questions,
            )
        return [k for seat, k in enumerate(batch) if chosen(answers, f"k{seat}") == "yes"]

    judged = await asyncio.gather(*(judge(b) for b in batches(keywords)))
    return [k for batch in judged for k in batch]


async def split_group(caller: Caller, group: list[str]) -> list[list[str]]:
    clusters: list[list[str]] = []
    pool = list(group)
    while pool:
        leader, others = pool[0], pool[1:]
        same: list[str] = []
        different: list[str] = []
        for batch in batches(others):
            questions = {
                f"k{seat}": choice(
                    f'Does a person searching "{keyword}" want the same thing as a person '
                    f'searching "{leader}"?',
                    SAME_RESULTS,
                )
                for seat, keyword in enumerate(batch)
            }
            answers = await ask(
                caller,
                {"task": "same_results", "leader": leader, "keywords": batch},
                {"main_keyword": leader},
                questions,
            )
            for seat, keyword in enumerate(batch):
                (same if chosen(answers, f"k{seat}") == "yes" else different).append(keyword)
        clusters.append([leader, *same])
        pool = different
    return clusters


async def split_groups(caller: Caller, groups: list[list[str]]) -> list[list[str]]:
    gate = asyncio.Semaphore(LLM_CONCURRENCY)

    async def run(group: list[str]) -> list[list[str]]:
        if len(group) == 1:
            return [group]
        async with gate:
            return await split_group(caller, group)

    split = await asyncio.gather(*(run(g) for g in groups))
    return [cluster for clusters in split for cluster in clusters]


async def intent_fits(caller: Caller, keyword: str, results: list[dict[str, Any]]) -> list[float]:
    if not results:
        return []
    questions = {
        f"r{seat}": choice(
            f'How well does result {seat + 1} serve a person searching "{keyword}"?', FITS
        )
        for seat in range(len(results))
    }
    answers = await ask(
        caller,
        {"task": "intent_fit", "keyword": keyword, "urls": [r["url"] for r in results]},
        {
            "search": keyword,
            "results": [
                {
                    "result": seat + 1,
                    "title": r.get("title"),
                    "url": r["url"],
                    "snippet": r.get("description"),
                }
                for seat, r in enumerate(results)
            ],
        },
        questions,
    )
    return [
        INTENT_FIT.get(chosen(answers, f"r{seat}") or "full", 1.0) for seat in range(len(results))
    ]
