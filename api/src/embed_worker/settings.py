from pydantic_settings import SettingsConfigDict

from src.core.env import EnvSettings


class WorkerSettings(EnvSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    meelu_embed_model: str = "Xenova/multilingual-e5-small"
    meelu_embed_interval_ms: int = 15000
    meelu_chunk_page_batch: int = 25
    meelu_embed_disabled: str = "0"
    meelu_embed_once: str = "0"
