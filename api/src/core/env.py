from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    @model_validator(mode="before")
    @classmethod
    def _blank_is_unset(cls, values: Any) -> Any:
        if isinstance(values, dict):
            return {key: value for key, value in values.items() if value != ""}
        return values
