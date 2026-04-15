from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    TAVILY_API_KEY: str
    CHATWOOT_BASE_URL: str
    CHATWOOT_ACCESS_TOKEN: str
    DATABASE_URL: str

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

config = Settings()
