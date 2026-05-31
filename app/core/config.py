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

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Backward-compatible module-level exports (used by existing service imports)
CLAUDE_API_KEY = settings.claude_api_key
CLAUDE_MODEL = settings.claude_model
CLAUDE_MAX_TOKENS = settings.claude_max_tokens
CLAUDE_TEMPERATURE = settings.claude_temperature
MONGODB_URL = settings.mongodb_url
MONGODB_DATABASE = settings.mongodb_database
