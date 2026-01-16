from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/meshtastic"
    meshtastic_device_name: Optional[str] = None  # Will scan for devices if not set

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
