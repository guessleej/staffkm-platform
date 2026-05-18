"""公開存取 API — 不需 JWT 的公開 Application 對話（workspace-aware）。

設計重點：
  - Endpoint 本身不掛 TenantContextMiddleware（路徑不含 /workspace/）。
  - 但 application 在 DB 內仍有 workspace_id；我們從該 row 取出後傳給
    AgentContext，使 RAG 呼叫 knowledge service 時能命中正確 workspace
    的知識庫，避免公開應用變成「跨 workspace 資料外洩管道」。
  - 公開應用必須 is_public = true，否則一律 404。
"""
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.application_agent import ApplicationAgent
from app.core.base_agent import AgentContext
from app.core.metering import meter_llm_call
from app.core.token_count import count_messages, count_text
from app.core.usage import QuotaExceeded
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils import database as _db
from staffkm_core.utils.database import get_session

router = APIRouter()


class PublicChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict] = Field(..., min_length=1)
    kb_ids: list[str] = Field(default_factory=list)
    # v3.7 P1：public chat 通常 stateless，預設不歸因；若 caller 傳則尊重
    conversation_id: str | None = None
    message_id: str | None = None


def _coerce_conv_id(body: "PublicChatRequest") -> str | None:
    raw = body.conversation_id
    if not raw:
        return None
    try:
        return str(uuid.UUID(str(raw)))
    except (TypeError, ValueError):
        return None


@router.get("/{app_id}", response_model=ApiResponse, summary="取得公開應用程式資訊")
async def get_public_application(
    app_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT id, name, description, icon, welcome_message, suggested_questions "
            "FROM applications "
            "WHERE id = :id AND status != 'deleted' AND is_public = true"
        ),
        {"id": str(app_id)},
    )
    app_row = row.fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail="應用程式不存在或未公開")
    d = dict(app_row._mapping)
    if isinstance(d.get("suggested_questions"), str):
        d["suggested_questions"] = json.loads(d["suggested_questions"])
    return ApiResponse(data=d)


@router.post("/{app_id}/chat", summary="公開應用程式對話（SSE，不需登入）")
async def public_chat(
    app_id: uuid.UUID,
    body: PublicChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT * FROM applications "
            "WHERE id = :id AND status != 'deleted' AND is_public = true"
        ),
        {"id": str(app_id)},
    )
    app_row = row.fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail="應用程式不存在或未公開")

    app_dict = dict(app_row._mapping)
    for field in ("suggested_questions", "knowledge_base_ids", "config"):
        if isinstance(app_dict.get(field), str):
            app_dict[field] = json.loads(app_dict[field])
        elif app_dict.get(field) is None:
            app_dict[field] = [] if field != "config" else {}

    # 從 application row 取出 workspace_id，傳給 AgentContext，
    # 讓 RAG 檢索能正確 scope 到該 workspace 的知識庫
    app_workspace_id = app_dict.get("workspace_id")
    app_workspace_id_str = str(app_workspace_id) if app_workspace_id else None

    agent = await ApplicationAgent.create(app_dict, session=session)
    ctx = AgentContext(
        session_id=body.session_id,
        user_id="public",
        messages=body.messages,
        kb_ids=body.kb_ids,
        workspace_id=app_workspace_id_str,
        # 公開存取無 RBAC 角色；knowledge service 若要授權需另設「public」角色
        roles=[],
    )

    model_hint = agent._model or "gpt-4o-mini"
    prompt_tokens_est = count_messages(body.messages, model=model_hint)

    async def event_generator():
        out_buffer: list[str] = []
        sess_factory = _db._session_factory
        # 公開存取 — 沒 workspace_id 就無法 meter，退化為純 streaming
        if sess_factory is None or not app_workspace_id_str:
            async for token in agent.stream_response(ctx):
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": token}
            yield {"event": "citations", "data": json.dumps(ctx.citations, ensure_ascii=False)}
            yield {"event": "done", "data": "[DONE]"}
            return

        async with sess_factory() as us_session:
            try:
                async with meter_llm_call(
                    us_session,
                    workspace_id=app_workspace_id_str,
                    user_id=None,  # 公開存取無 user
                    application_id=str(app_id),
                    provider_type=agent._provider_type,
                    model=agent._model,
                    conversation_id=_coerce_conv_id(body),
                    message_id=body.message_id,
                ) as meter:
                    try:
                        async for token in agent.stream_response(ctx):
                            if await request.is_disconnected():
                                break
                            out_buffer.append(token or "")
                            yield {"event": "token", "data": token}
                        yield {"event": "citations", "data": json.dumps(ctx.citations, ensure_ascii=False)}
                        yield {"event": "done", "data": "[DONE]"}
                    except Exception as e:
                        yield {"event": "error", "data": str(e)}
                        raise
                    finally:
                        meter.record(
                            prompt_tokens=prompt_tokens_est,
                            completion_tokens=count_text(
                                "".join(out_buffer), model=model_hint,
                            ),
                        )
            except QuotaExceeded as qe:
                yield {"event": "error", "data": f"quota_exceeded: {qe}"}
            except Exception:
                pass

    return EventSourceResponse(event_generator())
