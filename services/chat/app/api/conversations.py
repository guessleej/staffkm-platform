"""對話管理 API — 建立/查詢/刪除 Session 及訊息記錄"""
import json
import secrets
import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.models.conversation import Conversation, Message
from staffkm_core.schemas.response import ApiResponse, PagedResponse, PageMeta
from staffkm_core.utils.database import get_session

router = APIRouter()
public_router = APIRouter()
log = structlog.get_logger()


class ConversationCreate(BaseModel):
    scenario_id: str
    kb_ids: list[str] = []
    title: str | None = None


class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=4096)
    # v2.8：對話中動態切 model / KB（單次 override，不改 application 預設）
    model_override:  str | None = None
    kb_ids_override: list[str] | None = None


@router.post("", response_model=ApiResponse, summary="建立新對話 Session")
async def create_conversation(
    body: ConversationCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = getattr(request.state, "user_id", "anonymous")
    conv = Conversation(
        user_id=user_id,
        scenario_id=body.scenario_id,
        kb_ids=body.kb_ids,
        title=body.title or f"新對話 ({body.scenario_id})",
    )
    session.add(conv)
    await session.flush()
    return ApiResponse(data={"conversation_id": str(conv.id), "title": conv.title})


@router.get("", response_model=PagedResponse, summary="查詢對話清單")
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    user_id = getattr(request.state, "user_id", "anonymous")
    offset = (page - 1) * page_size
    result = await session.execute(
        select(Conversation).where(Conversation.user_id == user_id, Conversation.is_active == True)
        .order_by(Conversation.updated_at.desc())
        .offset(offset).limit(page_size)
    )
    convs = result.scalars().all()
    total = len(convs)
    return PagedResponse(
        data=[{
            "id": str(c.id), "title": c.title, "scenario_id": c.scenario_id,
            "message_count": c.message_count, "updated_at": c.updated_at.isoformat()
        } for c in convs],
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=max(1, -(-total // page_size))),
    )


@router.get("/{conv_id}/messages", response_model=ApiResponse, summary="取得對話訊息記錄")
async def get_messages(conv_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    conv = await session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")
    await session.refresh(conv, ["messages"])
    return ApiResponse(data=[
        {
            "id": str(m.id), "role": m.role, "content": m.content,
            "citations": m.citations, "created_at": m.created_at.isoformat(),
        }
        for m in conv.messages
    ])


@router.post("/{conv_id}/messages/stream", summary="串流發送訊息並取得 AI 回應")
async def stream_message(
    conv_id: uuid.UUID,
    body: ChatMessage,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    conv = await session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")

    # 儲存使用者訊息
    user_msg = Message(conversation_id=conv.id, role="user", content=body.content)
    session.add(user_msg)
    await session.flush()

    # 取得歷史訊息（最近 N 輪）
    result = await session.execute(
        select(Message).where(Message.conversation_id == conv_id)
        .order_by(Message.created_at).limit(settings.MAX_CONTEXT_MESSAGES)
    )
    history = result.scalars().all()
    messages = [{"role": m.role, "content": m.content} for m in history]
    await session.commit()

    async def event_generator():
        full_response = ""
        citations = []
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                upstream_kb_ids = body.kb_ids_override if body.kb_ids_override is not None else conv.kb_ids
                upstream_body = {
                    "scenario_id": conv.scenario_id,
                    "session_id": str(conv_id),
                    "messages": messages,
                    "kb_ids": upstream_kb_ids,
                }
                if body.model_override:
                    upstream_body["model_override"] = body.model_override
                async with client.stream(
                    "POST",
                    f"{settings.AGENT_SERVICE_URL}/api/v1/agents/{conv.scenario_id}/chat",
                    json=upstream_body,
                ) as upstream:
                    async for line in upstream.aiter_lines():
                        if await request.is_disconnected():
                            break
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if not data or data == "[DONE]":
                                continue
                            try:
                                parsed = json.loads(data)
                                if isinstance(parsed, list):
                                    citations = parsed
                                    continue
                            except json.JSONDecodeError:
                                pass
                            full_response += data
                            yield {"event": "token", "data": data}

            # 儲存 AI 回應
            async with session.begin():
                ai_msg = Message(
                    conversation_id=conv.id, role="assistant",
                    content=full_response, citations=citations,
                )
                session.add(ai_msg)
                conv.message_count = (conv.message_count or 0) + 2

            yield {"event": "citations", "data": json.dumps(citations, ensure_ascii=False)}
            yield {"event": "done", "data": "[DONE]"}

        except Exception as e:
            log.error("stream_failed", conv_id=str(conv_id), error=str(e))
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


@router.delete("/{conv_id}", response_model=ApiResponse, summary="刪除對話（soft delete）")
async def delete_conversation(
    conv_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    # v5.7.2: 補 ownership check — 之前任何人都能刪別人的對話
    user_id = getattr(request.state, "user_id", None) if request else None
    conv = await session.get(Conversation, conv_id)
    if not conv or not conv.is_active:
        raise HTTPException(status_code=404, detail="對話不存在")
    if user_id and conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="無權刪除此對話")
    conv.is_active = False
    # get_session yield 後自動 commit
    return ApiResponse(message="對話已刪除")


@router.get("/{conv_id}/export", summary="匯出對話記錄")
async def export_conversation(
    conv_id: uuid.UUID,
    format: str = "markdown",  # "markdown" | "json"
    session: AsyncSession = Depends(get_session),
):
    conv = await session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")

    msgs_result = await session.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()

    if format == "json":
        data = {
            "conversation": {
                "id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
            },
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ],
        }
        return FastAPIResponse(
            content=json.dumps(data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="conversation-{conv_id}.json"'},
        )
    else:  # markdown
        lines = [f"# {conv.title}\n", f"*匯出時間：{conv.created_at.strftime('%Y-%m-%d %H:%M')}*\n\n---\n"]
        for m in messages:
            role_label = "**使用者**" if m.role == "user" else "**助理**"
            lines.append(f"\n{role_label}\n\n{m.content}\n\n---\n")
        content = "".join(lines)
        return FastAPIResponse(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="conversation-{conv_id}.md"'},
        )


# ─────────────────────────────────────────────────────────────────────────────
# v2.7 — Share 對話紀錄
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/{conv_id}/share", response_model=ApiResponse, summary="產生分享連結（MaxKB v2.7）")
async def share_conversation(
    conv_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = getattr(request.state, "user_id", "anonymous")
    conv = await session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")
    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="無權分享他人對話")
    if not conv.share_token:
        conv.share_token = secrets.token_urlsafe(16)
    return ApiResponse(data={"share_token": conv.share_token})


@router.delete("/{conv_id}/share", response_model=ApiResponse, summary="撤銷分享連結")
async def revoke_share(
    conv_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = getattr(request.state, "user_id", "anonymous")
    conv = await session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")
    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="無權撤銷他人分享")
    conv.share_token = None
    return ApiResponse(message="分享連結已撤銷")


@public_router.get("/{share_token}", response_model=ApiResponse, summary="公開讀取分享對話")
async def get_public_conversation(
    share_token: str,
    session: AsyncSession = Depends(get_session),
):
    if not share_token or len(share_token) > 64:
        raise HTTPException(status_code=404, detail="分享連結無效")
    row = await session.execute(
        select(Conversation).where(
            Conversation.share_token == share_token,
            Conversation.is_active == True,  # noqa: E712
        )
    )
    conv = row.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="分享連結無效或已撤銷")
    msgs_result = await session.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()
    return ApiResponse(data={
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    })
