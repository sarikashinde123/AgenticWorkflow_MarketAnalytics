import os

from pydantic_settings import BaseSettings

_DEFAULT_REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")


class Settings(BaseSettings):
    anthropic_api_key: str
    database_url: str = "postgresql://user:password@localhost:5432/compintel"
    redis_url: str = "redis://localhost:6379/0"
    app_base_url: str = "http://localhost:8000"
    reports_dir: str = _DEFAULT_REPORTS_DIR

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
