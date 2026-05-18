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

    # v2.4-B：OIDC SSO（Google / Microsoft AD / Okta / Azure AD）
    OIDC_ENABLED:        bool = False
    OIDC_DISPLAY_NAME:   str  = "SSO"
    OIDC_ISSUER:         str  = ""
    OIDC_CLIENT_ID:      str  = ""
    OIDC_CLIENT_SECRET:  str  = ""
    OIDC_REDIRECT_URI:   str  = ""
    OIDC_SCOPES:         str  = "openid email profile"
    OIDC_DEFAULT_ROLE:   str  = "user"

    # v4.6 F: SMTP for verify-email / forgot-password / trial welcome
    # 沒設 SMTP_HOST 時 email dispatch 仍 log-only（dev 友善）
    SMTP_HOST:     str  = ""
    SMTP_PORT:     int  = 587
    SMTP_USER:     str  = ""
    SMTP_PASSWORD: str  = ""
    SMTP_FROM:     str  = "noreply@staffkm.local"
    SMTP_USE_TLS:  bool = True

    # v4.6 F: self-service OAuth (Google / GitHub) — 與 v2.4 企業 OIDC SSO 並行
    GOOGLE_OAUTH_CLIENT_ID:     str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_CLIENT_ID:     str = ""
    GITHUB_OAUTH_CLIENT_SECRET: str = ""

    # 帳號 verify / reset link 用的 frontend base URL（前端網址）
    PUBLIC_WEB_BASE_URL: str = "http://localhost"


settings = Settings()
