from pathlib import Path

from pydantic_settings import SettingsConfigDict

from src.core.env import EnvSettings


class Settings(EnvSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://craftmate:craftmate@localhost:5434/craftmate"
    database_pool_max: int = 20

    session_cookie_name: str = "meelu_session"
    session_lifetime_seconds: int = 60 * 60 * 24 * 30

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ]

    unsplash_access_key: str = ""

    log_level: str = "INFO"

    agent_data_dir: Path = Path.home() / ".meelu" / "agent-data"
    agent_statement_timeout_ms: int = 30000
    agent_work_mem: str = "64MB"
    agent_max_frame_rows: int = 200000
    agent_max_sql_rows: int = 500


settings = Settings()
