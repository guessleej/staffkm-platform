"""ORM models — workspace 與成員關聯。"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint, Index, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from staffkm_core.models.base import Base


class WorkspaceRole(str, Enum):
    """Workspace 4 級角色（粗粒度 RBAC）。"""
    OWNER  = "owner"
    ADMIN  = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

    @property
    def can_manage_workspace(self) -> bool:
        return self in (WorkspaceRole.OWNER,)

    @property
    def can_manage_members(self) -> bool:
        return self in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)

    @property
    def can_write(self) -> bool:
        return self in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.EDITOR)

    @property
    def can_read(self) -> bool:
        return True  # 所有成員都可讀


class Workspace(Base):
    """工作區 — 所有業務資源（KB / App / Model / Folder）的歸屬單位。"""
    __tablename__ = "workspace"
    __table_args__ = (
        Index("idx_workspace_slug", "slug", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name:        Mapped[str] = mapped_column(String(128), nullable=False)
    slug:        Mapped[str] = mapped_column(String(64),  nullable=False)  # URL-friendly 唯一識別
    description: Mapped[str | None] = mapped_column(String(512))
    plan:        Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    quota_meta:  Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Workspace {self.slug}>"


class WorkspaceMember(Base):
    """User 與 Workspace 的多對多關聯，含角色。"""
    __tablename__ = "workspace_member"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uniq_workspace_member"),
        Index("idx_member_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=WorkspaceRole.VIEWER.value)

    # 邀請 / 加入流程
    invited_by:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invited_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    joined_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    workspace: Mapped[Workspace] = relationship(back_populates="members")

    @property
    def role_enum(self) -> WorkspaceRole:
        return WorkspaceRole(self.role)
