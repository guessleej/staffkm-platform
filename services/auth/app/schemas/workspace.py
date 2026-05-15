"""Workspace API 的 Pydantic schemas (RFC-001 Stage 2)。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ─── Workspace ────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name:        str          = Field(..., min_length=1, max_length=128, description="工作區顯示名稱")
    slug:        str          = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                                      description="URL 識別子；小寫英數字 + 連字號")
    description: str | None   = Field(None, max_length=512)


class WorkspaceUpdate(BaseModel):
    name:        str | None   = Field(None, min_length=1, max_length=128)
    description: str | None   = Field(None, max_length=512)


class WorkspaceOut(BaseModel):
    id:          uuid.UUID
    name:        str
    slug:        str
    description: str | None
    plan:        str
    role:        str | None  = Field(None, description="呼叫者在此工作區的角色")
    member_count: int        = 0
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─── Member ───────────────────────────────────────────────────────────

class MemberInvite(BaseModel):
    user_id: uuid.UUID  = Field(..., description="既有 user 的 ID（v0.1 不做 email 邀請）")
    role:    str        = Field(default="viewer")

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        allowed = {"owner", "admin", "editor", "viewer"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class MemberRoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        allowed = {"owner", "admin", "editor", "viewer"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class MemberOut(BaseModel):
    user_id:    uuid.UUID
    username:   str | None
    display_name: str | None
    email:      str | None
    role:       str
    joined_at:  datetime | None
    invited_at: datetime
    is_active:  bool

    model_config = {"from_attributes": True}
