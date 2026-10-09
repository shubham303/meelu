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

    supabase_url: str = ""
    supabase_publishable_key: str = ""

    dodo_payments_api_key: str = ""
    dodo_payments_webhook_secret: str = ""
    dodo_payments_base_url: str = "https://test.dodopayments.com"
    dodo_payments_credits_product_id: str = ""
    dodo_payments_return_url: str = "http://localhost:3000/dashboard"
    payments_min_topup_usd: float = 5.0
    payments_max_topup_usd: float = 500.0

    dataforseo_auth: str = ""
    dataforseo_base_url: str = "https://api.dataforseo.com"
    apify_api_key: str = ""
    apify_max_charge_usd_per_run: float = 0.5
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api"
    openrouter_model: str = "deepseek/deepseek-v4.1-flash"
    credits_signup_grant_usd: float = 5.0
    credits_site_daily_usd: float = 0.4
    credits_minimum_balance_usd: float = 0.2
    credits_billing_period_hours: int = 24
    credits_billing_sweep_seconds: int = 300
    credits_billing_sweep_disabled: bool = False
    seo_job_vendor_ceiling_micros: int = 2_000_000

    log_level: str = "INFO"

    agent_data_dir: Path = Path.home() / ".meelu" / "agent-data"
    agent_statement_timeout_ms: int = 30000
    agent_work_mem: str = "64MB"
    agent_max_frame_rows: int = 200000
    agent_max_sql_rows: int = 500
    agent_max_workspace_rows: int = 50000
    agent_tenant_connections: int = 3


settings = Settings()
