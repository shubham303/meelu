import asyncio
from typing import Any

from src.providers.json_data_extractor.adapter import Question, choice
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.seo.keyword_clusters.constants import (
    LLM_BATCH,
    LLM_CONCURRENCY,
    RELEVANCE_BATCH,
)
from src.seo.keyword_clusters.schemas import KeywordLabels

RELEVANT = {
    "yes": "a real search a potential customer of this website could make, about what the seeds and the website are about",
    "no": "noise or off-topic: gibberish, another company's brand or login, jobs or salaries, piracy, a different meaning of a shared word, or a subject the website does not cover",
}

SAME_RESULTS = {
    "yes": "the same need: Google would show largely the same pages for both searches",
    "no": "a different need, product, audience or format: Google would show different pages",
}

INTENTS = {
    "informational": "wants to learn or understand something",
    "navigational": "wants one specific site, brand, login or page",
    "commercial": "is comparing products, services or providers before choosing one",
    "transactional": "wants to buy, sign up, book, hire or download now",
}

IMPORTANCE = {
    "hot": "ready to act on what this website offers: buy, sign up, book or get in touch",
    "warm": "researching or comparing options that this website could serve",
    "cold": "learning about the topic, far from needing what this website offers",
}

BRAND = {
    "yes": "names a company, brand, product or website, this one or any other",
    "no": "a general search that names no company, brand, product or website",
}


def batches(items: list[Any], size: int = LLM_BATCH) -> list[list[Any]]:
    return [items[start : start + size] for start in range(0, len(items), size)]


async def ask(
    caller: Caller, subject: dict[str, Any], state: Any, questions: dict[str, Question]
) -> dict[str, Any]:
    result = await json_data_extractor.decide(caller, subject, state, questions)
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

    judged = await asyncio.gather(*(judge(b) for b in batches(keywords, RELEVANCE_BATCH)))
    return [k for batch in judged for k in batch]


def brand_of(answer: str | None) -> bool | None:
    return None if answer is None else answer == "yes"


async def label_keywords(
    caller: Caller, website: dict[str, Any], keywords: list[str]
) -> dict[str, KeywordLabels]:
    gate = asyncio.Semaphore(LLM_CONCURRENCY)

    async def judge(batch: list[str]) -> dict[str, KeywordLabels]:
        questions: dict[str, Question] = {}
        for seat, keyword in enumerate(batch):
            questions[f"i{seat}"] = choice(
                f'What does a person searching "{keyword}" want?', INTENTS
            )
            questions[f"h{seat}"] = choice(
                f'How close is a person searching "{keyword}" to needing what this website offers?',
                IMPORTANCE,
            )
            questions[f"b{seat}"] = choice(f'Is "{keyword}" a brand search?', BRAND)
        async with gate:
            answers = await ask(
                caller,
                {"task": "keyword_labels", "website": website, "keywords": batch},
                {"website": website},
                questions,
            )
        return {
            keyword: KeywordLabels(
                intent=chosen(answers, f"i{seat}"),
                importance=chosen(answers, f"h{seat}"),
                is_brand_keyword=brand_of(chosen(answers, f"b{seat}")),
            )
            for seat, keyword in enumerate(batch)
        }

    labelled = await asyncio.gather(*(judge(b) for b in batches(keywords)))
    return {keyword: labels for part in labelled for keyword, labels in part.items()}


async def same_as(caller: Caller, leader: str, keywords: list[str]) -> tuple[list[str], list[str]]:
    same: list[str] = []
    different: list[str] = []
    for batch in batches(keywords):
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
    return same, different


async def split_group(caller: Caller, group: list[str], leaders: list[str]) -> list[list[str]]:
    clusters: list[list[str]] = []
    pool = list(group)
    for leader in leaders:
        if not pool:
            break
        same, pool = await same_as(caller, leader, pool)
        if same:
            clusters.append([leader, *same])
    while pool:
        leader, others = pool[0], pool[1:]
        same, pool = await same_as(caller, leader, others)
        clusters.append([leader, *same])
    return clusters


async def split_groups(
    caller: Caller, groups: list[tuple[list[str], list[str]]]
) -> list[list[str]]:
    gate = asyncio.Semaphore(LLM_CONCURRENCY)

    async def run(group: list[str], leaders: list[str]) -> list[list[str]]:
        if len(group) == 1 and not leaders:
            return [group]
        async with gate:
            return await split_group(caller, group, leaders)

    split = await asyncio.gather(*(run(g, leaders) for g, leaders in groups))
    return [cluster for clusters in split for cluster in clusters]
