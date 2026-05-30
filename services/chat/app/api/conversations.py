"""對話管理 API — 建立/查詢/刪除 Session 及訊息記錄"""
import asyncio
import json
import secrets
import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.models.conversation import Conversation, Message
from staffkm_core.schemas.response import ApiResponse, PagedResponse, PageMeta
from staffkm_core.utils import database as _db
from staffkm_core.utils.database import get_session

# v5.12: 串流生成的背景 task 強引用集合 — 即使 client 斷線，生成+存檔仍跑完（不被 GC、不被取消）
_stream_bg_tasks: set[asyncio.Task] = set()

router = APIRouter()
public_router = APIRouter()
log = structlog.get_logger()


class ConversationCreate(BaseModel):
    # v5.10.14：scenario_id（代理人）或 application_id（應用）二擇一
    scenario_id: str | None = None
    application_id: str | None = None
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
    if not body.scenario_id and not body.application_id:
        raise HTTPException(status_code=422, detail="需指定 scenario_id 或 application_id")
    default_title = (
        body.title
        or (f"新對話 ({body.scenario_id})" if body.scenario_id else "新對話")
    )
    conv = Conversation(
        user_id=user_id,
        scenario_id=body.scenario_id,
        application_id=uuid.UUID(body.application_id) if body.application_id else None,
        kb_ids=body.kb_ids,
        title=default_title,
    )
    session.add(conv)
    await session.flush()
    return ApiResponse(data={
        "conversation_id": str(conv.id),
        "title": conv.title,
        "application_id": str(conv.application_id) if conv.application_id else None,
        "scenario_id": conv.scenario_id,
    })


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
            "application_id": str(c.application_id) if c.application_id else None,
            "message_count": c.message_count, "updated_at": c.updated_at.isoformat()
        } for c in convs],
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=max(1, -(-total // page_size))),
    )


@router.get("/{conv_id}", response_model=ApiResponse, summary="取得單一對話詳情（deep-link / reload 載入用）")
async def get_conversation(conv_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)):
    """回單一對話的 metadata（含 application_id / scenario_id / kb_ids）。

    v5.12：前端深連結 /chat?conv=<id> 或重新整理時，記憶體清單沒這筆 → 用本端點 by-id
    取回對話脈絡（之前沒有此端點 → 前端載不到 → 畫面空白）。ownership check 同 get_messages。
    """
    conv = await session.get(Conversation, conv_id)
    if not conv or not conv.is_active:
        raise HTTPException(status_code=404, detail="對話不存在")
    user_id = getattr(request.state, "user_id", None)
    if user_id and conv.user_id not in (user_id, "anonymous"):
        raise HTTPException(status_code=403, detail="無權存取此對話")
    return ApiResponse(data={
        "id": str(conv.id),
        "title": conv.title,
        "scenario_id": conv.scenario_id,
        "application_id": str(conv.application_id) if conv.application_id else None,
        "kb_ids": conv.kb_ids,
        "message_count": conv.message_count,
        "is_active": conv.is_active,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    })


@router.get("/{conv_id}/messages", response_model=ApiResponse, summary="取得對話訊息記錄")
async def get_messages(conv_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)):
    conv = await session.get(Conversation, conv_id)
    if not conv or not conv.is_active:
        raise HTTPException(status_code=404, detail="對話不存在")
    # v5.12：補 ownership check — 之前任何人知道 conv_id 就能讀別人對話內容（IDOR）。
    # 對齊 delete_conversation 的判法（"anonymous" 對話視為公開）。公開分享走 /public 端點。
    user_id = getattr(request.state, "user_id", None)
    if user_id and conv.user_id not in (user_id, "anonymous"):
        raise HTTPException(status_code=403, detail="無權存取此對話")
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
    # v5.12：補 ownership check — 之前任何人知道/猜到 conv_id 就能往別人對話塞訊息、
    # 借別人對話脈絡拿 AI 回應（write-side IDOR）。對齊 get_messages / delete 的判法
    # （"anonymous" 對話視為公開）。檢查放在寫入使用者訊息之前。
    user_id = getattr(request.state, "user_id", None)
    if user_id and conv.user_id not in (user_id, "anonymous"):
        raise HTTPException(status_code=403, detail="無權存取此對話")

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

    # v5.9.10: agent service 自 v4.0 起只接 workspace-scoped 路徑
    # 從 gateway 注入的 X-Workspace-ID / X-User-ID / X-User-Roles 等都要轉發
    ws_id = request.headers.get("X-Workspace-ID", "")
    upstream_headers = {"Content-Type": "application/json"}
    for h in ("Authorization", "X-User-ID", "X-User-Roles", "X-Tenant-ID", "X-Workspace-ID"):
        v = request.headers.get(h)
        if v:
            upstream_headers[h] = v

    # v5.10.14：對話可綁 application（應用）或 scenario（代理人）→ 路由不同上游端點
    is_app = conv.application_id is not None

    # v5.12: 生成的 upstream URL/body 先算好（純值），供背景 task 閉包捕捉（不可在 task 內碰
    #   request-scoped 的 conv ORM 物件 — 斷線後 session 會關、conv 變 detached）。
    upstream_kb_ids = body.kb_ids_override if body.kb_ids_override is not None else conv.kb_ids
    ws_prefix = f"/workspace/{ws_id}" if ws_id else ""
    if is_app:
        upstream_body = {"session_id": str(conv_id), "messages": messages, "kb_ids": upstream_kb_ids or []}
        upstream_url = f"{settings.AGENT_SERVICE_URL}/api/v1{ws_prefix}/applications/{conv.application_id}/chat"
    else:
        upstream_body = {"scenario_id": conv.scenario_id, "session_id": str(conv_id),
                         "messages": messages, "kb_ids": upstream_kb_ids}
        upstream_url = f"{settings.AGENT_SERVICE_URL}/api/v1{ws_prefix}/agents/{conv.scenario_id}/chat"
    if body.model_override:
        upstream_body["model_override"] = body.model_override

    # v5.12: 生成+存檔放獨立背景 task（不綁 client 連線）。client 切走/斷線時，relay 被取消，
    #   但這個 task 繼續把答案生成完、用「自己的 session」存完整答案 → 切回來 reload 看到完整回答
    #   （原本：is_disconnected → break → 只存半截、上游 LLM 被中斷）。
    queue: asyncio.Queue = asyncio.Queue()

    async def _consume_and_persist():
        full_response = ""
        citations: list = []
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # 事件感知中繼：累積一個 event 的 data: 行，遇空行才用 \n 重組分派。
                ev_type = ""
                data_lines: list[str] = []
                async with client.stream("POST", upstream_url, json=upstream_body, headers=upstream_headers) as upstream:
                    async for raw in upstream.aiter_lines():
                        line = raw.rstrip("\r")
                        if line != "":
                            if line.startswith("event:"):
                                ev_type = line[6:].lstrip()
                            elif line.startswith("data:"):
                                s = line[5:]
                                data_lines.append(s[1:] if s.startswith(" ") else s)
                            continue
                        if not data_lines and not ev_type:
                            continue
                        data = "\n".join(data_lines)
                        etype = ev_type
                        ev_type = ""
                        data_lines = []
                        if etype == "tool_call":
                            await queue.put({"event": "tool_call", "data": data})
                        elif etype == "citations":
                            try: citations = json.loads(data)
                            except json.JSONDecodeError: pass
                        elif etype == "error":
                            await queue.put({"event": "error", "data": data})
                        elif etype == "done" or data == "[DONE]":
                            pass
                        else:
                            try:
                                parsed = json.loads(data)
                                if isinstance(parsed, list):
                                    citations = parsed
                                    continue
                            except json.JSONDecodeError:
                                pass
                            full_response += data
                            await queue.put({"event": "token", "data": data})

            # 用自己的 session 存（request session 在 client 斷線後可能已關閉）
            if full_response and _db._session_factory is not None:
                async with _db._session_factory() as s:
                    async with s.begin():
                        s.add(Message(conversation_id=conv_id, role="assistant",
                                      content=full_response, citations=citations))
                        await s.execute(text(
                            "UPDATE conversations SET message_count = COALESCE(message_count, 0) + 2 "
                            "WHERE id = :id"), {"id": str(conv_id)})

            await queue.put({"event": "citations", "data": json.dumps(citations, ensure_ascii=False)})
            await queue.put({"event": "done", "data": "[DONE]"})
        except Exception as e:
            log.error("stream_failed", conv_id=str(conv_id), error=str(e))
            await queue.put({"event": "error", "data": str(e)})
        finally:
            await queue.put(None)  # sentinel：通知 relay 結束

    task = asyncio.create_task(_consume_and_persist())
    _stream_bg_tasks.add(task)                      # 強引用，避免被 GC
    task.add_done_callback(_stream_bg_tasks.discard)

    async def event_generator():
        # 純 relay：client 斷線時這裡被 sse-starlette 取消，但上面的 task 不取消、繼續存檔
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return EventSourceResponse(event_generator())


@router.delete("/{conv_id}", response_model=ApiResponse, summary="刪除對話（soft delete）")
async def delete_conversation(
    conv_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    # v5.7.2: 補 ownership check — 之前任何人都能刪別人的對話
    # v5.9.13: 例外放行 anonymous 對話（早期版本未登入建立的、誰登入都能清）
    user_id = getattr(request.state, "user_id", None) if request else None
    conv = await session.get(Conversation, conv_id)
    if not conv or not conv.is_active:
        raise HTTPException(status_code=404, detail="對話不存在")
    if user_id and conv.user_id not in (user_id, "anonymous"):
        raise HTTPException(status_code=403, detail="無權刪除此對話")
    conv.is_active = False
    # get_session yield 後自動 commit
    return ApiResponse(message="對話已刪除")


@router.get("/{conv_id}/export", summary="匯出對話記錄")
async def export_conversation(
    conv_id: uuid.UUID,
    format: str = "markdown",  # "markdown" | "json"
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    # v5.12: 補 ownership check — export 是 read-side IDOR 漏網（get_messages/delete/share 早已補）。
    # 知道/猜到 conv_id 即可匯出他人完整對話 → 與 get_messages 同類，對齊處理。
    user_id = getattr(request.state, "user_id", None) if request else None
    conv = await session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")
    if user_id and conv.user_id not in (user_id, "anonymous"):
        raise HTTPException(status_code=403, detail="無權匯出此對話")

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
