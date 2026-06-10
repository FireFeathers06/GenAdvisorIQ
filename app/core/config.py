from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # Claude AI
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 2000
    claude_temperature: float = 0.7

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "genadvisoriq"

    # Auth — set JWT_SECRET_KEY in .env for production; the random default
    # invalidates all sessions on every restart.
    jwt_secret_key: str = ""
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 7

    # Chat proxy guardrails
    chat_daily_token_budget: int = 200_000   # per advisor per day
    chat_max_output_tokens: int = 1500       # server-side cap per request
    chat_max_request_chars: int = 60_000     # total message payload size limit
    chat_max_messages: int = 40              # max turns per request

    # Transport security
    cors_allowed_origins: str = ""           # comma-separated; empty = no CORS (same-origin only)
    allowed_hosts: str = "*"                 # comma-separated for TrustedHostMiddleware

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if not settings.jwt_secret_key:
    import secrets as _secrets
    import warnings
    settings.jwt_secret_key = _secrets.token_urlsafe(48)
    warnings.warn(
        "JWT_SECRET_KEY not set — generated an ephemeral secret. "
        "All sessions will be invalidated on restart. Set it in .env for production."
    )

# Backward-compatible module-level exports (used by existing service imports)
CLAUDE_API_KEY = settings.claude_api_key
CLAUDE_MODEL = settings.claude_model
CLAUDE_MAX_TOKENS = settings.claude_max_tokens
CLAUDE_TEMPERATURE = settings.claude_temperature
MONGODB_URL = settings.mongodb_url
MONGODB_DATABASE = settings.mongodb_database
