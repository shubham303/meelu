from datetime import timedelta
from typing import Any

from src.providers.json_data_extractor.adapter import DECIDE, Question
from src.providers.json_data_extractor.openrouter_deepseek import OpenRouterDeepSeekAdapter
from src.providers.registry import Caller, ProviderFacade

TTL = timedelta(days=90)


class JsonDataExtractor(ProviderFacade):
    domain = "json-data-extractor"
    label = "structured extraction"

    async def decide(
        self,
        caller: Caller,
        subject: dict[str, Any],
        state: Any,
        questions: dict[str, Question],
    ) -> dict[str, Any]:
        return await self.fetch(
            caller,
            DECIDE,
            lambda _: {"subject": subject, "questions": questions},
            lambda a: a.decide(state, questions),
            TTL,
        )


json_data_extractor = JsonDataExtractor([OpenRouterDeepSeekAdapter()])
