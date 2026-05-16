"""串流對話 API — SSE 即時回應，附引用來源（workspace-scoped）"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_agent import AgentContext
from app.core.application_agent import ApplicationAgent
from app.core.usage import QuotaExceeded, UsageRecord, check_quota, record_usage
from staffkm_core.utils import database as _db
from app.scenarios import SCENARIO_REGISTRY
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member

router = APIRouter()


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

    # M3 收尾：呼叫前先檢查 workspace quota
    try:
        await check_quota(session, str(ctx_t.workspace_id))
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))

    agent = await ApplicationAgent.create(app_dict, session=session)

    ctx = AgentContext(
        session_id=body.session_id,
        user_id=str(ctx_t.user_id),
        messages=body.messages,
        kb_ids=body.kb_ids,
        workspace_id=str(ctx_t.workspace_id),
        roles=[ctx_t.role.value],
    )

    # 粗估 prompt tokens：以「字元 / 4」近似（中英文混合最穩；後續可換 tiktoken）
    def _approx_tokens(s: str) -> int:
        return max(1, len(s) // 4)

    prompt_text = "\n".join(m.get("content", "") for m in body.messages if m.get("content"))
    prompt_tokens_est = _approx_tokens(prompt_text)

    async def event_generator():
        import time
        start = time.monotonic()
        out_chars = 0
        status = "ok"
        err: str | None = None
        try:
            async for token in agent.stream_response(ctx):
                if await request.is_disconnected():
                    status = "client_disconnect"
                    break
                out_chars += len(token or "")
                yield {"event": "token", "data": token}

            yield {
                "event": "citations",
                "data": json.dumps(ctx.citations, ensure_ascii=False),
            }
            yield {"event": "done", "data": "[DONE]"}

        except Exception as e:
            status, err = "error", str(e)
            yield {"event": "error", "data": str(e)}

        # M3 收尾：寫一筆 usage log（用獨立 session，避免請求 session 已關閉）
        try:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            completion_tokens_est = _approx_tokens("x" * out_chars) if out_chars else 0
            sess_factory = _db._session_factory
            if sess_factory is not None:
                async with sess_factory() as us_session:
                    await record_usage(us_session, UsageRecord(
                        workspace_id=str(ctx_t.workspace_id),
                        user_id=str(ctx_t.user_id),
                        application_id=str(app_id),
                        provider_type=agent._provider_type,
                        model=agent._model,
                        prompt_tokens=prompt_tokens_est,
                        completion_tokens=completion_tokens_est,
                        total_tokens=prompt_tokens_est + completion_tokens_est,
                        latency_ms=elapsed_ms,
                        status=status,
                        error=err,
                    ))
                    await us_session.commit()
        except Exception as log_err:
            # 計帳失敗不影響使用者體驗
            yield {"event": "usage_log_error", "data": str(log_err)}

    return EventSourceResponse(event_generator())
