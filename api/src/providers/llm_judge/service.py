from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.llm_judge.adapter import JUDGE, JsonSchema
from src.providers.llm_judge.openrouter_chat import OpenRouterChatJudge
from src.providers.registry import Caller, ProviderFacade

TTL = timedelta(days=30)


class LlmJudge(ProviderFacade):
    domain = "llm-judge"
    label = "model judgement"

    async def judge(
        self,
        db: AsyncSession,
        caller: Caller,
        subject: dict[str, Any],
        instructions: str,
        state: Any,
        schema: JsonSchema,
    ) -> dict[str, Any]:
        return await self.fetch(
            db,
            caller,
            JUDGE,
            {"subject": subject, "instructions": instructions, "schema": schema},
            lambda a: a.judge(instructions, state, schema),
            TTL,
        )


llm_judge = LlmJudge([OpenRouterChatJudge()])
