"""Arq settings — v4.0 P3。

worker service 跟 enqueue caller 共用。把 REDIS_URL（v3.0-P1 CAPTCHA 已用）
parse 成 arq 需要的 RedisSettings。
"""
from __future__ import annotations

import os

from arq.connections import RedisSettings

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")


def parse_redis_url(url: str) -> RedisSettings:
    """parse redis URL 成 arq RedisSettings。

    支援格式：redis://[:password@]host:port/db
    """
    from urllib.parse import urlparse

    p = urlparse(url)
    return RedisSettings(
        host=p.hostname or "redis",
        port=p.port or 6379,
        password=p.password,
        database=int((p.path or "/0").lstrip("/") or "0"),
    )


REDIS_SETTINGS = parse_redis_url(REDIS_URL)
