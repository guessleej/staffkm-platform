"""使用者資料模型"""
import uuid
from enum import Enum

from sqlalchemy import String, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base, UUIDPrimaryKeyMixin, AuditMixin


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
    status: Mapped[str] = mapped_column(String(32), default=UserStatus.ACTIVE)
    roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    department: Mapped[str | None] = mapped_column(String(128))
    tenant_id: Mapped[str | None] = mapped_column(String(64))
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
