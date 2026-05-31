from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RSS_FEED: AnyHttpUrl
    REFRESH_INTERVAL: int = 300
    PUSHOVER_TOKEN: str
    PUSHOVER_USERS: list[str]

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()
