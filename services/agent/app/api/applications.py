"""應用程式管理 API — Application Builder CRUD（workspace-scoped）。

權限模型：
  list / get / suggested-questions / chat   require_member  （成員可看可用）
  create / update / delete                  require_writer / require_admin
"""
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_agent import AgentContext
from app.core.application_agent import ApplicationAgent
from staffkm_core.schemas.response import ApiResponse, PagedResponse, PageMeta
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member, require_writer

router = APIRouter()


# ── Pydantic Schemas ────────────────────────────────────────────────────────


class ApplicationCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: str | None = None
    icon: str | None = None
    type: str = Field(default="simple", pattern="^(simple|workflow)$")
    status: str = Field(default="published", pattern="^(draft|published|deleted)$")
    llm_model_id: uuid.UUID | None = None
    system_prompt: str | None = None
    welcome_message: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)
    knowledge_base_ids: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    is_public: bool = False
    tenant_id: str | None = None


class ApplicationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    description: str | None = None
    icon: str | None = None
    type: str | None = Field(default=None, pattern="^(simple|workflow)$")
    status: str | None = Field(default=None, pattern="^(draft|published|deleted)$")
    llm_model_id: uuid.UUID | None = None
    system_prompt: str | None = None
    welcome_message: str | None = None
    suggested_questions: list[str] | None = None
    knowledge_base_ids: list[str] | None = None
    config: dict[str, Any] | None = None
    is_public: bool | None = None


class ApplicationOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    icon: str | None
    type: str
    status: str
    llm_model_id: uuid.UUID | None
    system_prompt: str | None
    welcome_message: str | None
    suggested_questions: list[str]
    knowledge_base_ids: list[str]
    config: dict[str, Any]
    is_public: bool
    tenant_id: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None


def _row_to_out(row) -> ApplicationOut:
    """將資料庫 Row 物件轉換為 ApplicationOut（過濾掉非 schema 欄位如 workspace_id）。"""
    d = dict(row._mapping)
    for field in ("suggested_questions", "knowledge_base_ids", "config"):
        if isinstance(d.get(field), str):
            d[field] = json.loads(d[field])
        elif d.get(field) is None:
            d[field] = [] if field != "config" else {}
    # 只保留 ApplicationOut 定義的欄位
    return ApplicationOut(**{k: v for k, v in d.items() if k in ApplicationOut.model_fields})


# ── 列表 ────────────────────────────────────────────────────────────────────


@router.get("", response_model=PagedResponse[ApplicationOut], summary="列出所有應用程式")
async def list_applications(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size

    where_clause = "WHERE a.workspace_id = :workspace_id AND a.status != 'deleted'"
    params: dict[str, Any] = {
        "workspace_id": str(ctx.workspace_id),
        "limit": page_size,
        "offset": offset,
    }
    if status:
        where_clause += " AND a.status = :status"
        params["status"] = status

    rows = await session.execute(
        text(
            f"""
            SELECT a.*
            FROM applications a
            {where_clause}
            ORDER BY a.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    applications = rows.fetchall()

    count_row = await session.execute(
        text(f"SELECT COUNT(*) FROM applications a {where_clause}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    )
    total = count_row.scalar() or 0

    return PagedResponse(
        data=[_row_to_out(r) for r in applications],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=-(-total // page_size),
        ),
    )


# ── 建立 ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ApiResponse[ApplicationOut],
    status_code=status.HTTP_201_CREATED,
    summary="建立新應用程式（writer 以上）",
)
async def create_application(
    body: ApplicationCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    new_id = uuid.uuid4()
    now = datetime.utcnow()

    await session.execute(
        text(
            """
            INSERT INTO applications (
                id, workspace_id, name, description, icon, type, status,
                llm_model_id, system_prompt, welcome_message,
                suggested_questions, knowledge_base_ids, config,
                is_public, tenant_id, created_at, updated_at, created_by
            ) VALUES (
                :id, :workspace_id, :name, :description, :icon, :type, :status,
                :llm_model_id, :system_prompt, :welcome_message,
                :suggested_questions::jsonb, :knowledge_base_ids::jsonb, :config::jsonb,
                :is_public, :tenant_id, :created_at, :updated_at, :created_by
            )
            """
        ),
        {
            "id": str(new_id),
            "workspace_id": str(ctx.workspace_id),
            "name": body.name,
            "description": body.description,
            "icon": body.icon,
            "type": body.type,
            "status": body.status,
            "llm_model_id": str(body.llm_model_id) if body.llm_model_id else None,
            "system_prompt": body.system_prompt,
            "welcome_message": body.welcome_message,
            "suggested_questions": json.dumps(body.suggested_questions, ensure_ascii=False),
            "knowledge_base_ids": json.dumps(body.knowledge_base_ids, ensure_ascii=False),
            "config": json.dumps(body.config, ensure_ascii=False),
            "is_public": body.is_public,
            "tenant_id": body.tenant_id,
            "created_at": now,
            "updated_at": now,
            "created_by": str(ctx.user_id),
        },
    )

    row = await session.execute(
        text("SELECT * FROM applications WHERE id = :id"),
        {"id": str(new_id)},
    )
    app_row = row.fetchone()
    if not app_row:
        raise HTTPException(status_code=500, detail="應用程式建立失敗")

    return ApiResponse(data=_row_to_out(app_row), message="應用程式建立成功")


# ── 取得單筆 ────────────────────────────────────────────────────────────────


@router.get("/{app_id}", response_model=ApiResponse[ApplicationOut], summary="取得應用程式詳情")
async def get_application(
    app_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT * FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    app_row = row.fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail="應用程式不存在")

    return ApiResponse(data=_row_to_out(app_row))


# ── 更新 ────────────────────────────────────────────────────────────────────


@router.put(
    "/{app_id}",
    response_model=ApiResponse[ApplicationOut],
    summary="更新應用程式（writer 以上）",
)
async def update_application(
    app_id: uuid.UUID,
    body: ApplicationUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    check = await session.execute(
        text(
            "SELECT id FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="應用程式不存在")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="未提供任何更新欄位")

    set_parts: list[str] = ["updated_at = :updated_at", "updated_by = :updated_by"]
    params: dict[str, Any] = {
        "id": str(app_id),
        "ws": str(ctx.workspace_id),
        "updated_at": datetime.utcnow(),
        "updated_by": str(ctx.user_id),
    }

    for field, value in updates.items():
        if field in ("suggested_questions", "knowledge_base_ids", "config"):
            set_parts.append(f"{field} = :{field}::jsonb")
            params[field] = json.dumps(value, ensure_ascii=False)
        elif field == "llm_model_id":
            set_parts.append(f"{field} = :{field}")
            params[field] = str(value) if value else None
        else:
            set_parts.append(f"{field} = :{field}")
            params[field] = value

    await session.execute(
        text(
            f"UPDATE applications SET {', '.join(set_parts)} "
            f"WHERE id = :id AND workspace_id = :ws"
        ),
        params,
    )

    row = await session.execute(
        text("SELECT * FROM applications WHERE id = :id"),
        {"id": str(app_id)},
    )
    return ApiResponse(data=_row_to_out(row.fetchone()), message="應用程式更新成功")


# ── 刪除（軟刪除）──────────────────────────────────────────────────────────


@router.delete(
    "/{app_id}",
    response_model=ApiResponse,
    summary="刪除應用程式（admin 以上，軟刪除）",
)
async def delete_application(
    app_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    check = await session.execute(
        text(
            "SELECT id FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="應用程式不存在")

    await session.execute(
        text(
            "UPDATE applications SET status = 'deleted', updated_at = :now, updated_by = :uid "
            "WHERE id = :id AND workspace_id = :ws"
        ),
        {
            "id": str(app_id),
            "ws": str(ctx.workspace_id),
            "now": datetime.utcnow(),
            "uid": str(ctx.user_id),
        },
    )
    return ApiResponse(message="應用程式已刪除")


# ── 建議問題 ────────────────────────────────────────────────────────────────


@router.get(
    "/{app_id}/suggested-questions",
    response_model=ApiResponse[list[str]],
    summary="取得應用程式建議問題",
)
async def get_suggested_questions(
    app_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT suggested_questions FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    app_row = row.fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail="應用程式不存在")

    questions = app_row._mapping["suggested_questions"]
    if isinstance(questions, str):
        questions = json.loads(questions)
    if questions is None:
        questions = []

    return ApiResponse(data=questions)


# ── 串流對話 ────────────────────────────────────────────────────────────────


class AppChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict] = Field(..., min_length=1)
    kb_ids: list[str] = Field(default_factory=list)


@router.post(
    "/{app_id}/chat",
    summary="與 Application Builder 應用程式對話（SSE 串流）",
)
async def chat_with_application(
    app_id: uuid.UUID,
    body: AppChatRequest,
    request: Request,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT * FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    app_row = row.fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail=f"應用程式 '{app_id}' 不存在")

    app_dict = dict(app_row._mapping)
    for field in ("suggested_questions", "knowledge_base_ids", "config"):
        if isinstance(app_dict.get(field), str):
            app_dict[field] = json.loads(app_dict[field])
        elif app_dict.get(field) is None:
            app_dict[field] = [] if field != "config" else {}

    agent = await ApplicationAgent.create(app_dict, session=session)

    chat_ctx = AgentContext(
        session_id=body.session_id,
        user_id=str(ctx.user_id),
        messages=body.messages,
        kb_ids=body.kb_ids,
        workspace_id=str(ctx.workspace_id),
        roles=[ctx.role.value],
    )

    async def event_generator():
        try:
            async for token in agent.stream_response(chat_ctx):
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": token}
            yield {"event": "citations", "data": json.dumps(chat_ctx.citations, ensure_ascii=False)}
            yield {"event": "done", "data": "[DONE]"}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
