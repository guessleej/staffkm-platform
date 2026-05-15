"""Microsoft Teams Bot 整合連接器"""
import httpx
import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import settings

log = structlog.get_logger()
router = APIRouter()


class TeamsActivity(BaseModel):
    type: str
    id: str | None = None
    text: str | None = None
    from_: dict | None = None
    conversation: dict | None = None
    channelId: str | None = None
    serviceUrl: str | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


async def _ask_agent(user_message: str, session_id: str) -> str:
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
            )
            answer = ""
            for line in resp.text.splitlines():
                if line.startswith("data:") and not line.strip().endswith("[DONE]"):
                    token = line[5:].strip()
                    if token and not token.startswith("{"):
                        answer += token
            return answer or "抱歉，目前無法回應，請稍後再試。"
    except Exception as e:
        log.error("agent_call_failed", error=str(e))
        return "系統暫時無法回應，請稍後再試。"


async def _send_teams_reply(service_url: str, conversation_id: str, activity_id: str, text: str):
    """透過 Bot Framework REST API 回覆 Teams 訊息。"""
    token_resp = httpx.post(
        "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": settings.TEAMS_APP_ID,
            "client_secret": settings.TEAMS_APP_PASSWORD,
            "scope": "https://api.botframework.com/.default",
        },
    )
    access_token = token_resp.json().get("access_token", "")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{service_url}v3/conversations/{conversation_id}/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"type": "message", "text": text},
        )


@router.post("/teams/webhook", summary="Teams Bot Webhook 接收端點")
async def teams_webhook(request: Request):
    body = await request.json()
    activity_type = body.get("type", "")
    if activity_type != "message":
        return {"status": "ignored"}

    user_text = body.get("text", "").strip()
    conversation_id = body.get("conversation", {}).get("id", "")
    activity_id = body.get("id", "")
    service_url = body.get("serviceUrl", "")
    from_id = body.get("from", {}).get("id", "unknown")

    if user_text:
        session_id = f"teams_{from_id}"
        answer = await _ask_agent(user_text, session_id)
        await _send_teams_reply(service_url, conversation_id, activity_id, answer)

    return {"status": "ok"}
