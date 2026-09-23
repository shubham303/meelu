from typing import Any

from src.providers.registry import ProviderAdapter, VendorResponse

JUDGE = "judge"

JsonSchema = dict[str, Any]


class LlmJudgeAdapter(ProviderAdapter):
    async def judge(self, instructions: str, state: Any, schema: JsonSchema) -> VendorResponse:
        raise self.unsupported(JUDGE)
