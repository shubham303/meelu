from typing import Any

from src.providers.registry import ProviderAdapter, VendorResponse

DECIDE = "decide"
EXTRACT = "extract"

Question = dict[str, Any]


def choice(instructions: str, options: dict[str, str]) -> Question:
    return {"type": "choice", "instructions": instructions, "criteria": options}


def boolean(instructions: str, when_true: str, when_false: str) -> Question:
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {"true": when_true, "false": when_false},
    }


def score(instructions: str, levels: list[str]) -> Question:
    return {"type": "score", "instructions": instructions, "criteria": levels}


class JsonDataExtractorAdapter(ProviderAdapter):
    async def decide(self, state: Any, questions: dict[str, Question]) -> VendorResponse:
        raise self.unsupported(DECIDE)

    async def extract(self, instructions: str, data: Any, schema: dict[str, Any]) -> VendorResponse:
        raise self.unsupported(EXTRACT)
