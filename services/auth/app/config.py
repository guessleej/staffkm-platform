from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_URL: str = "postgresql+asyncpg://staffkm:staffkm_secret@postgres:5432/staffkm?ssl=disable"
    REDIS_URL: str = "redis://:staffkm_redis@redis:6379/3"
    SECRET_KEY: str = "changeme"
    JWT_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_DAYS: int = 30

    LDAP_ENABLED: bool = False
    LDAP_SERVER: str = "ldap://localhost:389"
    LDAP_BASE_DN: str = ""
    LDAP_BIND_DN: str = ""
    LDAP_BIND_PASSWORD: str = ""


settings = Settings()
