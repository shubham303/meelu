import hashlib
import json
from datetime import timedelta
from typing import Any

from src.providers.json_data_extractor.adapter import DECIDE, EXTRACT, Question
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

    async def extract(
        self,
        caller: Caller,
        subject: dict[str, Any],
        instructions: str,
        data: Any,
        schema: dict[str, Any],
        ttl: timedelta | None = None,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(
            json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return await self.fetch(
            caller,
            EXTRACT,
            lambda _: {
                "subject": subject,
                "instructions": instructions,
                "schema": schema,
                "data": digest,
            },
            lambda a: a.extract(instructions, data, schema),
            ttl,
        )


json_data_extractor = JsonDataExtractor([OpenRouterDeepSeekAdapter()])
