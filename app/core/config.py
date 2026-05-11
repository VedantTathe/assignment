from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Agent Orchestrator"
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/appdb"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.deepseek.com"
    MODEL_NAME: str = "deepseek-chat"

    class Config:
        env_file = ".env"

settings = Settings()
