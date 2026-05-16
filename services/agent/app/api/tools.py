"""Tools API — 工具獨立模組（RFC-006 新 backlog）。

kind: http / mcp / shell / custom
config: 依 kind 不同；http 例：{"url": "...", "method": "POST", "headers": {...}}
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.api._generic_crud import make_crud_router


class ToolOut(BaseModel):
    id:           uuid.UUID
    workspace_id: uuid.UUID
    name:         str
    description:  str | None
    kind:         str
    config:       dict[str, Any]
    is_enabled:   bool
    created_at:   datetime
    updated_at:   datetime
    created_by:   uuid.UUID | None
    updated_by:   uuid.UUID | None


class ToolCreate(BaseModel):
    name:        str = Field(..., max_length=128)
    description: str | None = None
    kind:        str = Field(default="http")
    config:      dict[str, Any] = Field(default_factory=dict)
    is_enabled:  bool = True


class ToolUpdate(BaseModel):
    name:        str | None = Field(default=None, max_length=128)
    description: str | None = None
    kind:        str | None = None
    config:      dict[str, Any] | None = None
    is_enabled:  bool | None = None


router = make_crud_router(
    table="tools",
    out_model=ToolOut,
    create_model=ToolCreate,
    update_model=ToolUpdate,
    jsonb_fields=("config",),
)
