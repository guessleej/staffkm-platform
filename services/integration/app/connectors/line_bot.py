"""LINE Bot 整合連接器"""
import hashlib
import hmac
import base64

import httpx
import structlog
from fastapi import APIRouter, Request, HTTPException, Header
from linebot.v3 import WebhookParser
from linebot.v3.messaging import AsyncApiClient, AsyncMessagingApi, Configuration, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.config import settings

log = structlog.get_logger()
router = APIRouter()

_configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
_parser = WebhookParser(settings.LINE_CHANNEL_SECRET)


def _verify_signature(body: bytes, signature: str) -> bool:
    # v5.12：secret 未設定一律拒（不可把「未設定連接器」當開放 → 否則 HMAC("",body) 可偽造簽章）。
    secret = settings.LINE_CHANNEL_SECRET or ""
    if not secret:
        log.warning("line_webhook_rejected_no_secret")
        return False
    hash_val = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(hash_val).decode(), signature or "")


async def _ask_agent(user_message: str, session_id: str) -> str:
    """轉發到 Agent Service 取得回應（非串流版本，適用 LINE/Teams）。"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AGENT_SERVICE_URL}/api/v1/agents/sop/chat",
                json={
                    "scenario_id": "sop",
                    "session_id": session_id,
                    "messages": [{"role": "user", "content": user_message}],
                    "kb_ids": [],
                },
                headers={"Accept": "text/event-stream"},
            )
            # 收集 SSE 資料
            answer = ""
            for line in resp.text.splitlines():
                if line.startswith("data:") and not line.strip().endswith("[DONE]"):
                    event_type = ""
                    if '"event":"token"' in line or line.startswith("data:"):
                        token = line[5:].strip()
                        if token and not token.startswith("{"):
                            answer += token
            return answer or "抱歉，目前無法回應您的問題，請稍後再試。"
    except Exception as e:
        log.error("agent_call_failed", error=str(e))
        return "系統暫時無法回應，請稍後再試或聯繫管理員。"


@router.post("/line/webhook", summary="LINE Webhook 接收端點")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(alias="X-Line-Signature"),
):
    body = await request.body()
    if not _verify_signature(body, x_line_signature):
        raise HTTPException(status_code=400, detail="無效的 LINE 簽章")

    try:
        events = _parser.parse(body.decode(), x_line_signature)
    except Exception as e:
        log.error("line_parse_failed", error=str(e))
        raise HTTPException(status_code=400, detail="解析 LINE 事件失敗")

    async with AsyncApiClient(_configuration) as api_client:
        line_api = AsyncMessagingApi(api_client)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                user_text = event.message.text
                session_id = f"line_{event.source.user_id}"
                answer = await _ask_agent(user_text, session_id)
                await line_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=answer)],
                    )
                )

    return {"status": "ok"}
