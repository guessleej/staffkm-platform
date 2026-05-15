"""公開存取 API — 不需 JWT 的公開 Application 對話"""
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.application_agent import ApplicationAgent
from app.core.base_agent import AgentContext
from core.schemas.response import ApiResponse
from core.utils.database import get_session

router = APIRouter()


class PublicChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict] = Field(..., min_length=1)
    kb_ids: list[str] = Field(default_factory=list)


@router.get("/{app_id}", response_model=ApiResponse, summary="取得公開應用程式資訊")
async def get_public_application(app_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    row = await session.execute(
        text(
            "SELECT id, name, description, icon, welcome_message, suggested_questions "
            "FROM applications WHERE id = :id AND status != 'deleted' AND is_public = true"
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
        text("SELECT * FROM applications WHERE id = :id AND status != 'deleted' AND is_public = true"),
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

    agent = await ApplicationAgent.create(app_dict, session=session)
    ctx = AgentContext(
        session_id=body.session_id,
        user_id="public",
        messages=body.messages,
        kb_ids=body.kb_ids,
    )

    async def event_generator():
        try:
            async for token in agent.stream_response(ctx):
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": token}
            yield {"event": "citations", "data": json.dumps(ctx.citations, ensure_ascii=False)}
            yield {"event": "done", "data": "[DONE]"}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
