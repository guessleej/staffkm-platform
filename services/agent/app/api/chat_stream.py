"""串流對話 API — SSE 即時回應，附引用來源（workspace-scoped）"""
import json
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_agent import AgentContext
from app.core.application_agent import ApplicationAgent
from app.core.token_count import count_messages, count_text
from app.core.metering import meter_llm_call
from app.core.usage import QuotaExceeded
from staffkm_core.utils import database as _db
from app.scenarios import SCENARIO_REGISTRY
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member

router = APIRouter()
log = structlog.get_logger()


# ── 場景代理人（舊有，向下相容）────────────────────────────────────────────


class ChatRequest(BaseModel):
    scenario_id: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict] = Field(..., min_length=1)
    kb_ids: list[str] = Field(default_factory=list)


@router.post("/{scenario_id}/chat", summary="與代理人對話（SSE 串流）")
async def chat_with_agent(
    scenario_id: str,
    body: ChatRequest,
    request: Request,
    ctx_t: TenantContext = Depends(require_member),
):
    if scenario_id not in SCENARIO_REGISTRY:
        raise HTTPException(status_code=404, detail=f"代理人 '{scenario_id}' 不存在")

    agent_cls = SCENARIO_REGISTRY[scenario_id]
    agent = agent_cls()

    ctx = AgentContext(
        session_id=body.session_id,
        user_id=str(ctx_t.user_id),
        messages=body.messages,
        kb_ids=body.kb_ids,
        workspace_id=str(ctx_t.workspace_id),
        roles=[ctx_t.role.value],
    )

    async def event_generator():
        try:
            async for token in agent.stream_response(ctx):
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": token}

            yield {
                "event": "citations",
                "data": json.dumps(ctx.citations, ensure_ascii=False),
            }
            yield {"event": "done", "data": "[DONE]"}

        except Exception as e:
            log.error("scenario_stream_failed", error=str(e))  # v5.12: 原本只回前端 error event、後端無痕
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


# ── Application Builder 代理人（DB 驅動）────────────────────────────────────


class AppChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict] = Field(..., min_length=1)
    kb_ids: list[str] = Field(
        default_factory=list,
        description="額外補充的知識庫 IDs（合併 application 設定的 kb_ids）",
    )
    # v3.7 P1：per-conversation cost 歸因；前端未傳會 fallback 用 session_id（若為 UUID）
    conversation_id: str | None = None
    message_id: str | None = None


def _coerce_conv_id(body: "AppChatRequest") -> str | None:
    """從 body 取 conversation_id；fallback: session_id（前端目前傳 conv id 進 session_id）。"""
    raw = body.conversation_id or body.session_id
    if not raw:
        return None
    try:
        return str(uuid.UUID(str(raw)))
    except (TypeError, ValueError):
        return None


# Sprint 19-B preview chat：移到 applications.py 內，因為它才是
# 前端真正打的 /api/v1/applications/* 對應 router。


@router.post(
    "/applications/{app_id}/chat",
    summary="與 Application Builder 應用程式對話（SSE 串流）",
    tags=["Application Builder"],
)
async def chat_with_application(
    app_id: uuid.UUID,
    body: AppChatRequest,
    request: Request,
    ctx_t: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # 從 DB 取得 application 設定（同 workspace 才看得到）
    row = await session.execute(
        text(
            "SELECT * FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(ctx_t.workspace_id)},
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

    ctx = AgentContext(
        session_id=body.session_id,
        user_id=str(ctx_t.user_id),
        messages=body.messages,
        kb_ids=body.kb_ids,
        workspace_id=str(ctx_t.workspace_id),
        roles=[ctx_t.role.value],
    )

    # Round 8-4：用 tiktoken 精算 prompt tokens（fallback char/4 內建在 count_messages）
    model_hint = agent._model or "gpt-4o-mini"
    prompt_tokens_est = count_messages(body.messages, model=model_hint)

    async def event_generator():
        out_buffer: list[str] = []
        # 用獨立 session 給 metering（避免請求 session 在 SSE 結束前已關閉）；
        # quota pre-check 也在 context manager 進入時跑，超額 raise QuotaExceeded
        # → 由 main.py 的 exception handler 轉 429。
        sess_factory = _db._session_factory
        if sess_factory is None:
            # 沒 DB 設定時退化為純 streaming（理論上不該發生）
            async for ev in agent.stream_events(ctx):
                if await request.is_disconnected():
                    break
                if ev.get("type") == "tool_call":
                    yield {"event": "tool_call", "data": json.dumps(ev, ensure_ascii=False)}
                elif ev.get("type") == "token":
                    yield {"event": "token", "data": ev.get("data") or ""}
            yield {"event": "citations", "data": json.dumps(ctx.citations, ensure_ascii=False)}
            yield {"event": "done", "data": "[DONE]"}
            return

        async with sess_factory() as us_session:
            try:
                async with meter_llm_call(
                    us_session,
                    workspace_id=str(ctx_t.workspace_id),
                    user_id=str(ctx_t.user_id),
                    application_id=str(app_id),
                    provider_type=agent._provider_type,
                    model=agent._model,
                    conversation_id=_coerce_conv_id(body),
                    message_id=body.message_id,
                    feature="chat",
                ) as meter:
                    try:
                        async for ev in agent.stream_events(ctx):
                            if await request.is_disconnected():
                                break
                            if ev.get("type") == "tool_call":
                                # 任務 3：tool_call SSE event（前端 ToolCallBlock 顯示）
                                yield {
                                    "event": "tool_call",
                                    "data": json.dumps(ev, ensure_ascii=False),
                                }
                            elif ev.get("type") == "token":
                                token = ev.get("data") or ""
                                out_buffer.append(token)
                                yield {"event": "token", "data": token}

                        yield {
                            "event": "citations",
                            "data": json.dumps(ctx.citations, ensure_ascii=False),
                        }
                        yield {"event": "done", "data": "[DONE]"}
                    except Exception as e:
                        yield {"event": "error", "data": str(e)}
                        raise
                    finally:
                        # Round 8-4：對輸出字串做精算
                        completion_tokens_est = count_text(
                            "".join(out_buffer), model=model_hint,
                        )
                        meter.record(
                            prompt_tokens=prompt_tokens_est,
                            completion_tokens=completion_tokens_est,
                        )
            except QuotaExceeded as qe:
                # quota 超額：pre-check 階段就 raise；SSE 已開，回一個 error event
                yield {"event": "error", "data": f"quota_exceeded: {qe}"}
            except Exception:
                # 已在內層 yield error；這裡 swallow 避免 SSE 異常傳出 ASGI
                pass

    return EventSourceResponse(event_generator())
