from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    AGENT_SERVICE_URL: str = "http://agent:8002"
    LINE_CHANNEL_SECRET: str = ""
    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    TEAMS_APP_ID: str = ""
    TEAMS_APP_PASSWORD: str = ""


settings = Settings()
