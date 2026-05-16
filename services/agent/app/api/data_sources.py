"""Data Sources API — DB / API 連接器（RFC-006 新 backlog）。

kind: postgres / mysql / mongo / rest / graphql / s3 ...
config: 依 kind 不同；postgres 例：{"host": "...", "port": 5432, "database": "...", "user": "..."}

注意：本檔只負責 metadata CRUD；實際同步 / 查詢由外部 worker（之後再加）。
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.api._generic_crud import make_crud_router


class DataSourceOut(BaseModel):
    id:              uuid.UUID
    workspace_id:    uuid.UUID
    name:            str
    description:     str | None
    kind:            str
    config:          dict[str, Any]
    is_enabled:      bool
    last_synced_at:  datetime | None
    created_at:      datetime
    updated_at:      datetime
    created_by:      uuid.UUID | None
    updated_by:      uuid.UUID | None


class DataSourceCreate(BaseModel):
    name:        str = Field(..., max_length=128)
    description: str | None = None
    kind:        str = Field(default="postgres")
    config:      dict[str, Any] = Field(default_factory=dict)
    is_enabled:  bool = True


class DataSourceUpdate(BaseModel):
    name:        str | None = Field(default=None, max_length=128)
    description: str | None = None
    kind:        str | None = None
    config:      dict[str, Any] | None = None
    is_enabled:  bool | None = None


router = make_crud_router(
    table="data_sources",
    out_model=DataSourceOut,
    create_model=DataSourceCreate,
    update_model=DataSourceUpdate,
    jsonb_fields=("config",),
)
