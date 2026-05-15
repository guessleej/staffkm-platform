"""串流對話 API — SSE 即時回應，附引用來源"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_agent import AgentContext
from app.core.application_agent import ApplicationAgent
from app.scenarios import SCENARIO_REGISTRY
from staffkm_core.utils.database import get_session

router = APIRouter()


# ── 場景代理人（舊有，向下相容）────────────────────────────────────────────


class ChatRequest(BaseModel):
    scenario_id: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict] = Field(..., min_length=1)
    kb_ids: list[str] = Field(default_factory=list)


@router.post("/{scenario_id}/chat", summary="與代理人對話（SSE 串流）")
async def chat_with_agent(scenario_id: str, body: ChatRequest, request: Request):
    if scenario_id not in SCENARIO_REGISTRY:
        raise HTTPException(status_code=404, detail=f"代理人 '{scenario_id}' 不存在")

    agent_cls = SCENARIO_REGISTRY[scenario_id]
    agent = agent_cls()

    ctx = AgentContext(
        session_id=body.session_id,
        user_id=request.headers.get("X-User-ID", "anonymous"),
        messages=body.messages,
        kb_ids=body.kb_ids,
    )

    async def event_generator():
        try:
            async for token in agent.stream_response(ctx):
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": token}

            # 傳送引用來源
            yield {
                "event": "citations",
                "data": json.dumps(ctx.citations, ensure_ascii=False),
            }
            yield {"event": "done", "data": "[DONE]"}

        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


# ── Application Builder 代理人（DB 驅動）────────────────────────────────────


class AppChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict] = Field(..., min_length=1)
    kb_ids: list[str] = Field(default_factory=list, description="額外補充的知識庫 IDs（合併 application 設定的 kb_ids）")


@router.post(
    "/applications/{app_id}/chat",
    summary="與 Application Builder 應用程式對話（SSE 串流）",
    tags=["Application Builder"],
)
async def chat_with_application(
    app_id: uuid.UUID,
    body: AppChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # 從 DB 取得 application 設定
    row = await session.execute(
        text(
            "SELECT * FROM applications WHERE id = :id AND status != 'deleted'"
        ),
        {"id": str(app_id)},
    )
    app_row = row.fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail=f"應用程式 '{app_id}' 不存在")

    # 將 Row 轉為 dict，JSONB 欄位若為字串則解析
    app_dict = dict(app_row._mapping)
    for field in ("suggested_questions", "knowledge_base_ids", "config"):
        if isinstance(app_dict.get(field), str):
            app_dict[field] = json.loads(app_dict[field])
        elif app_dict.get(field) is None:
            app_dict[field] = [] if field != "config" else {}

    # 建立 ApplicationAgent（非同步工廠，會從 DB 載入 LLM 設定）
    agent = await ApplicationAgent.create(app_dict, session=session)

    ctx = AgentContext(
        session_id=body.session_id,
        user_id=request.headers.get("X-User-ID", "anonymous"),
        messages=body.messages,
        kb_ids=body.kb_ids,
    )

    async def event_generator():
        try:
            async for token in agent.stream_response(ctx):
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": token}

            # 傳送引用來源
            yield {
                "event": "citations",
                "data": json.dumps(ctx.citations, ensure_ascii=False),
            }
            yield {"event": "done", "data": "[DONE]"}

        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
