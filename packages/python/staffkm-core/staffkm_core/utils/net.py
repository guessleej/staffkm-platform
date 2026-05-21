"""SSRF 防護：驗證對外 URL 不指向內網 / loopback / 雲端 metadata。

背景：workflow `http_request` 節點、知識庫 web sync、MCP server 連線都吃
使用者（或 workspace 設定）給的 URL。沒設防的話攻擊者可讓伺服器去打
`http://169.254.169.254/...`（雲端 metadata）或內網服務 → SSRF。
（對標 MaxKB v2.9.1 修的 CVE-2026-45412 同一類攻擊面。）

用法：
    from staffkm_core.utils.net import assert_safe_url, safe_request, UnsafeURLError

    await assert_safe_url(url)                      # 不安全 → raise UnsafeURLError
    resp = await safe_request(client, "GET", url)   # 驗證 + 逐跳 redirect 再驗證

注意（已知殘留風險）：assert_safe_url 解析後到實際連線之間仍有 TOCTOU
（DNS rebinding）窗口；要完全消除需把連線 pin 到已驗證 IP（後續硬化項）。
本模組已擋掉「直接給內網位址」與「DNS 解析指向內網」與「redirect 跳內網」
三種主要途徑，相較原本零防護是實質改善。

頂層僅 import 標準庫；httpx 在 safe_request 內 lazy import，
讓只需 assert_safe_url 的環境（如 CI 單元測試）免裝 httpx 也能 import。
"""
from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit

_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECTS = 5


def _env_allowed_hosts() -> set[str]:
    """operator 明確信任的 host allowlist（env `SSRF_ALLOWED_HOSTS`，逗號分隔）。

    deny-by-default：預設空集合 → 所有私網位址都擋。
    需要讓 workflow http_request 呼叫內部服務時，把該服務 host
    （如 `knowledge,agent,chat`）加進此 env 即可繞過 IP 網段檢查。
    """
    raw = os.environ.get("SSRF_ALLOWED_HOSTS", "")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


class UnsafeURLError(ValueError):
    """URL 指向被禁止的目標（內網 / loopback / metadata / 非法 scheme / 內嵌憑證）。"""


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """判斷 IP 是否落在禁止網段。

    link_local 含 169.254.0.0/16，涵蓋 AWS/GCP/Azure 的 169.254.169.254 metadata。
    IPv4-mapped IPv6（::ffff:10.0.0.1 之類）先攤平成 IPv4 再判，避免繞過。
    """
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _resolve_all(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return list({info[4][0] for info in infos})


async def assert_safe_url(url: str, *, allow_hosts: set[str] | None = None) -> str:
    """驗證 URL 安全並回傳原 URL；不安全 raise UnsafeURLError。

    檢查：scheme allowlist（http/https）、無內嵌帳密、host 解析出的
    每個 IP 都不在禁止網段（同時擋「直接給 IP」與「DNS 指向內網」）。

    allow_hosts（與 env `SSRF_ALLOWED_HOSTS` 合併）內的 host 跳過 IP 網段檢查，
    供 workflow 呼叫內部服務等明確信任場景使用（scheme / 憑證檢查仍生效）。
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(f"不允許的 URL scheme：{parts.scheme!r}（僅允許 http/https）")
    if parts.username or parts.password:
        raise UnsafeURLError("URL 不可內嵌帳密憑證")
    host = parts.hostname
    if not host:
        raise UnsafeURLError("URL 缺少 host")
    allowed = _env_allowed_hosts() | {h.lower() for h in (allow_hosts or set())}
    if host.lower() in allowed:
        return url
    port = parts.port or (443 if scheme == "https" else 80)
    try:
        ips = await _resolve_all(host, port)
    except (socket.gaierror, OSError) as exc:
        raise UnsafeURLError(f"無法解析 host {host!r}：{exc}") from exc
    if not ips:
        raise UnsafeURLError(f"host {host!r} 無 DNS 解析結果")
    for ip_s in ips:
        try:
            ip = ipaddress.ip_address(ip_s)
        except ValueError as exc:
            raise UnsafeURLError(f"無效解析結果 {ip_s!r}") from exc
        if _ip_is_blocked(ip):
            raise UnsafeURLError(f"URL 指向被禁止的位址 {ip}（host={host}）")
    return url


async def safe_request(
    client,
    method: str,
    url: str,
    *,
    max_redirects: int = _MAX_REDIRECTS,
    allow_hosts: set[str] | None = None,
    **kwargs,
):
    """以 SSRF guard 包裝 httpx 請求：驗證初始 URL，且逐跳驗證 redirect 目標。

    不論傳入 client 原本的 follow_redirects 設定，這裡一律手動跟隨，
    每跳都先 assert_safe_url，避免「初始 URL 合法但 302 跳內網」的繞過。
    """
    kwargs.pop("follow_redirects", None)  # 由本函式接管
    current = url
    for _ in range(max_redirects + 1):
        await assert_safe_url(current, allow_hosts=allow_hosts)
        resp = await client.request(method, current, follow_redirects=False, **kwargs)
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("location")
            if loc:
                current = urljoin(current, loc)
                continue
        return resp
    raise UnsafeURLError(f"redirect 次數超過上限（{max_redirects}）")
