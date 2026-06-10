"""使用者資料模型"""
import uuid
from enum import Enum

from sqlalchemy import String, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from staffkm_core.models.base import Base, UUIDPrimaryKeyMixin, AuditMixin


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"


class User(Base, UUIDPrimaryKeyMixin, AuditMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(256), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(128))
    password_hash: Mapped[str | None] = mapped_column(String(256))
    ldap_dn: Mapped[str | None] = mapped_column(String(512))
    # v3.0：OIDC SSO 正規欄位（之前借用 ldap_dn 存 oidc:{sub}，v3 起獨立）
    oidc_sub: Mapped[str | None] = mapped_column(String(256), index=True)
    oidc_issuer: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default=UserStatus.ACTIVE)
    roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    department: Mapped[str | None] = mapped_column(String(128))
    tenant_id: Mapped[str | None] = mapped_column(String(64))
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    # v2.7 X-Pack：每位使用者可被限定的登入方式
    # NULL = 不限制；非 NULL 時必須為以下值的子集：
    #   password / oidc / google / github / ldap / local
    allowed_login_methods: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=None,
    )
    # v5.12：首次登入強制改密 — 出廠預設 admin 帳號設 true（init.sql），改密後清除。
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # v5.13 #2：記住上次使用的 workspace（跨裝置/來源）。前端切 workspace 時寫回。
    last_workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
