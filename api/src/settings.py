from pathlib import Path

from pydantic import field_validator
from pydantic_settings import SettingsConfigDict

from src.core.env import EnvSettings


class Settings(EnvSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://craftmate:craftmate@localhost:5434/craftmate"
    database_pool_max: int = 20
    migrate_database_url: str | None = None

    session_cookie_name: str = "meelu_session"
    session_lifetime_seconds: int = 60 * 60 * 24 * 30
    session_cookie_secure: bool = True
    session_purge_minutes: int = 60

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ]
    app_origins: list[str] = []
    api_docs_enabled: bool = False

    unsplash_access_key: str = ""

    auth_jwks_url: str = ""
    auth_issuer: str = ""
    auth_audience: str = ""

    dodo_payments_api_key: str = ""
    dodo_payments_webhook_secret: str = ""
    dodo_payments_base_url: str = "https://test.dodopayments.com"
    dodo_payments_credits_product_id: str = ""
    dodo_payments_return_url: str = "https://meelu.tech/payment-complete"
    payments_min_topup_usd: float = 5.0
    payments_max_topup_usd: float = 500.0

    dataforseo_auth: str = ""
    dataforseo_base_url: str = "https://api.dataforseo.com"
    dataforseo_chatgpt_model: str = "gpt-6-luna"
    dataforseo_claude_model: str = "claude-haiku-5-5"
    apify_api_key: str = ""
    composio_api_key: str = ""
    composio_base_url: str = "https://backend.composio.dev/api/v3.1"
    github_token: str = ""
    stackexchange_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api"
    openrouter_model: str = "deepseek/deepseek-v4.1-flash"

    llm_default_model: str = "anthropic/claude-haiku-5.5"
    llm_featured_models: list[str] = [
        "anthropic/claude-haiku-5.5",
        "deepseek/deepseek-v4-flash",
        "openai/gpt-6-luna",
    ]
    llm_catalog_ttl_seconds: int = 6 * 60 * 60
    llm_stream_timeout_seconds: float = 600.0
    llm_stream_max_seconds: float = 1200.0
    credits_trial_days: int = 3
    credits_site_daily_usd: float = 0.4
    credits_site_daily_discounted_usd: float = 0.2
    credits_full_price_sites: int = 5
    credits_minimum_balance_usd: float = 0.2
    credits_parallel_calls_per_user: int = 10
    credits_slot_wait_seconds: float = 60.0
    llm_max_output_tokens: int = 32_000
    llm_max_request_mb: float = 20.0
    credits_billing_period_hours: int = 24
    credits_billing_sweep_seconds: int = 300
    credits_billing_sweep_disabled: bool = False
    sites_paused_retention_days: int = 30
    sites_purge_minutes: int = 60
    connected_apps_sweep_minutes: int = 60
    seo_job_vendor_ceiling_micros: int = 2_000_000

    log_level: str = "INFO"
    log_slow_request_ms: int = 1000
    sentry_dsn: str = ""
    sentry_environment: str = "local"

    agent_data_dir: Path = Path.home() / ".meelu" / "agent-data"
    agent_statement_timeout_ms: int = 30000
    agent_work_mem: str = "64MB"
    agent_max_frame_rows: int = 200000
    agent_max_sql_rows: int = 500
    agent_max_workspace_rows: int = 50000
    agent_tenant_connections: int = 3
    agent_allowed_hosts: list[str] = ["127.0.0.1:*", "localhost:*", "agent:8484"]
    agent_max_workspace_bytes: int = 2 * 1024**3
    agent_max_result_bytes: int = 5 * 1024**2
    agent_max_frame_bytes: int = 256 * 1024**2
    agent_tool_concurrency: int = 4
    agent_temp_file_limit: str = "1GB"
    agent_max_models: int = 50
    agent_workspace_ttl_days: int = 7
    agent_workspace_sweep_minutes: int = 60

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard_origin(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("CORS_ORIGINS cannot contain '*': the api sends credentialed cookies.")
        return origins


settings = Settings()
