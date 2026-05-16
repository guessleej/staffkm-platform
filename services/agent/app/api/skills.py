"""Skills API — 可重用 prompt 技能（RFC-006 新 backlog）。

prompt_template 內可帶 {{var}} 變數，由 variables 宣告 schema。
任何 Application / 對話可呼叫此 Skill 注入 prompt。
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.api._generic_crud import make_crud_router


class SkillOut(BaseModel):
    id:              uuid.UUID
    workspace_id:    uuid.UUID
    name:            str
    description:     str | None
    prompt_template: str
    variables:       list[dict[str, Any]]
    tags:            list[str]
    created_at:      datetime
    updated_at:      datetime
    created_by:      uuid.UUID | None
    updated_by:      uuid.UUID | None


class SkillCreate(BaseModel):
    name:            str = Field(..., max_length=128)
    description:     str | None = None
    prompt_template: str = Field(default="")
    variables:       list[dict[str, Any]] = Field(default_factory=list)
    tags:            list[str] = Field(default_factory=list)


class SkillUpdate(BaseModel):
    name:            str | None = Field(default=None, max_length=128)
    description:     str | None = None
    prompt_template: str | None = None
    variables:       list[dict[str, Any]] | None = None
    tags:            list[str] | None = None


router = make_crud_router(
    table="skills",
    out_model=SkillOut,
    create_model=SkillCreate,
    update_model=SkillUpdate,
    jsonb_fields=("variables", "tags"),
)
