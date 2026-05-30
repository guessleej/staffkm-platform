"""Microsoft Teams Bot 整合連接器"""
import asyncio
from urllib.parse import urlparse

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import settings

log = structlog.get_logger()
router = APIRouter()

# v5.12：Bot Connector 簽發入站 Activity 的 JWT 簽章/簽發者。
# 驗證 issuer + audience(=Bot App ID) + RS256 簽章，擋未認證者直接 POST 驅動 agent。
# 注意：PyJWT 採 lazy import（函式內）→ 萬一容器尚未 rebuild 裝 pyjwt，也只讓 Teams 驗證
# fail-closed（回 401），不會在模組載入時炸掉整個 integration service（含 LINE）。
_BOTFRAMEWORK_ISSUER = "https://api.botframework.com"
_BOTFRAMEWORK_JWKS = "https://login.botframework.com/v1/.well-known/keys"
_jwks_client = None  # type: ignore[var-annotated]


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        from jwt import PyJWKClient  # lazy
        # PyJWKClient 內建 key 快取（lifespan）→ 不會每次請求都抓 JWKS。
        _jwks_client = PyJWKClient(_BOTFRAMEWORK_JWKS)
    return _jwks_client


async def _verify_inbound_jwt(auth_header: str) -> bool:
    """驗證 Teams/Bot Connector 入站 JWT。JWKS 抓取 + 簽章驗證為同步（urllib）→
    丟 threadpool 避免阻塞 event loop。驗不過 / pyjwt 未裝皆回 False（fail-closed）。"""
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return False
    token = auth_header[7:].strip()

    def _decode():
        import jwt  # lazy
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.TEAMS_APP_ID,
            issuer=_BOTFRAMEWORK_ISSUER,
            options={"require": ["exp", "iss", "aud"]},
        )

    try:
        await asyncio.get_event_loop().run_in_executor(None, _decode)
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("teams_inbound_jwt_invalid", error=str(e)[:120])
        return False


def _is_trusted_service_url(url: str) -> bool:
    """v5.12：serviceUrl 取自 webhook body（攻擊者可控）。回覆時會帶 bot 的 AAD token POST 過去
    → 若不限制，attacker 設 serviceUrl=自己主機可竊 token + SSRF。只放行 Bot Framework 官方主機。"""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return False
    return host.endswith(".botframework.com") or host.endswith(".trafficmanager.net")


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
    # v5.12：原本用同步 httpx.post 取 token → 在 async webhook 內會「阻塞整個 event loop」
    # （Teams 一來訊息、token 端點慢回，integration service 含 LINE 全卡）。改全 async + timeout。
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.TEAMS_APP_ID,
                "client_secret": settings.TEAMS_APP_PASSWORD,
                "scope": "https://api.botframework.com/.default",
            },
        )
        access_token = token_resp.json().get("access_token", "")

        await client.post(
            f"{service_url}v3/conversations/{conversation_id}/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"type": "message", "text": text},
        )


@router.post("/teams/webhook", summary="Teams Bot Webhook 接收端點")
async def teams_webhook(request: Request):
    # v5.12：未設定連接器一律拒（不可把未設定當開放）。
    if not settings.TEAMS_APP_ID or not settings.TEAMS_APP_PASSWORD:
        raise HTTPException(status_code=503, detail="Teams 連接器未設定")
    # v5.12：驗證 Bot Connector 入站 JWT — 否則未認證者可直接 POST 驅動 agent
    # （消耗 LLM 配額 / prompt injection / 對 botframework 任意 conversation 發訊息）。
    if not await _verify_inbound_jwt(request.headers.get("authorization", "")):
        raise HTTPException(status_code=401, detail="入站 JWT 驗證失敗")
    body = await request.json()
    activity_type = body.get("type", "")
    if activity_type != "message":
        return {"status": "ignored"}

    user_text = body.get("text", "").strip()
    conversation_id = body.get("conversation", {}).get("id", "")
    activity_id = body.get("id", "")
    service_url = body.get("serviceUrl", "")
    from_id = body.get("from", {}).get("id", "unknown")

    # v5.12：serviceUrl 必須是 Bot Framework 官方主機才回覆（否則 bot 的 AAD token 會被竊）。
    if service_url and not _is_trusted_service_url(service_url):
        log.warning("teams_webhook_untrusted_service_url", service_url=service_url[:80])
        raise HTTPException(status_code=400, detail="不信任的 serviceUrl")

    if user_text:
        session_id = f"teams_{from_id}"
        answer = await _ask_agent(user_text, session_id)
        await _send_teams_reply(service_url, conversation_id, activity_id, answer)

    return {"status": "ok"}
