"""Email dispatch — thin wrapper around aiosmtplib (v3.4 P2)。

SMTP 設定來自 `settings.SMTP_*`：沒設 SMTP_HOST → `send_email()` 直接 log skip、
回 False；上層應視為「未送出」處理（quota_alert worker 已 catch warning）。

不做 retry — 上層 worker 下個回合會重新評估、若未消化 threshold 會再嘗試。
"""
from __future__ import annotations

import structlog

from app.config import settings

log = structlog.get_logger()


async def send_email(*, to: str, subject: str, body: str, html: bool = False) -> bool:
    """送一封 email；回 True 表示成功 handed off 到 SMTP server。

    SMTP 未配置（SMTP_HOST 空）→ 直接 log skip、回 False；不視為錯誤。
    """
    if not settings.SMTP_HOST:
        log.info("email_skipped_no_smtp_config", to=to, subject=subject)
        return False
    try:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"]    = settings.SMTP_FROM
        msg["To"]      = to
        msg["Subject"] = subject
        if html:
            msg.set_content(body, subtype="html")
        else:
            msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_USE_TLS,
        )
        log.info("email_sent", to=to, subject=subject)
        return True
    except Exception as e:
        log.warning("email_send_failed", to=to, error=str(e))
        return False
