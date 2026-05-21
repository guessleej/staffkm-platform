"""SSRF guard 單元測試（P0-2）。

驗證 staffkm_core.utils.net.assert_safe_url：
- 擋內網 / loopback / 雲端 metadata / 非法 scheme / 內嵌憑證
- 放行公網位址
- env SSRF_ALLOWED_HOSTS 可放行指定 host（內部服務呼叫）

全程用 IP literal / 環境變數，不需網路（getaddrinfo 對數字位址離線解析）。
net.py 頂層只 import 標準庫（httpx lazy），故 CI 免裝 httpx 即可跑。
"""
import asyncio
import os
import pathlib
import sys

import pytest

# CI 不 pip install staffkm_core，手動把套件目錄加到 path
_PKG = pathlib.Path(__file__).resolve().parents[1] / "packages/python/staffkm-core"
sys.path.insert(0, str(_PKG))

from staffkm_core.utils.net import UnsafeURLError, assert_safe_url  # noqa: E402


def _check(url: str) -> str:
    return asyncio.run(assert_safe_url(url))


BLOCKED = [
    "http://127.0.0.1/",                    # loopback
    "http://169.254.169.254/latest/meta-data/",  # 雲端 metadata
    "http://10.0.0.5/internal",             # RFC1918
    "http://192.168.1.1/",                  # RFC1918
    "http://172.16.0.1/",                   # RFC1918
    "http://[::1]/",                        # IPv6 loopback
    "http://0.0.0.0/",                      # unspecified
    "file:///etc/passwd",                   # 非法 scheme
    "gopher://127.0.0.1:6379/_INFO",        # 非法 scheme
    "http://user:pass@8.8.8.8/",            # 內嵌憑證
    "http://[::ffff:10.0.0.1]/",            # IPv4-mapped IPv6 繞過
]


@pytest.mark.parametrize("url", BLOCKED)
def test_blocked_urls_raise(url):
    with pytest.raises(UnsafeURLError):
        _check(url)


def test_public_ip_allowed():
    # 公網 IP literal（離線解析回自身）→ 應通過
    assert _check("http://8.8.8.8/") == "http://8.8.8.8/"


def test_env_allowlist_bypasses_private(monkeypatch):
    # 預設：內部 host 被擋（假設解析得到，但這裡用 IP 直接驗私網擋）
    monkeypatch.delenv("SSRF_ALLOWED_HOSTS", raising=False)
    with pytest.raises(UnsafeURLError):
        _check("http://10.1.2.3/")
    # 加進 allowlist 後，allowlist 比對 host 字串、在 DNS 解析前短路放行
    monkeypatch.setenv("SSRF_ALLOWED_HOSTS", "knowledge,agent")
    assert _check("http://knowledge:8001/api/v1/health") == "http://knowledge:8001/api/v1/health"


def test_allowlist_still_enforces_scheme(monkeypatch):
    monkeypatch.setenv("SSRF_ALLOWED_HOSTS", "knowledge")
    with pytest.raises(UnsafeURLError):
        _check("file://knowledge/etc/passwd")
