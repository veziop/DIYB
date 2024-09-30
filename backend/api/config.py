import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    timezone: str = os.getenv("TIMEZONE", "Europe/Madrid")


settings = Settings()
