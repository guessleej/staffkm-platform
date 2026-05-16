"""staffKM Python SDK — 對接 v2 API 的輕量 client。

用法：
    from staffkm_sdk import StaffKMClient

    client = StaffKMClient(
        base_url="https://staffkm.example.com",
        api_key="sk-...",            # 從 admin/api-keys 取得
        workspace_id="...",
    )

    # 同步 chat（一次性 response）
    print(client.chat(app_id="...", message="今天天氣？").content)

    # SSE 串流
    for chunk in client.chat_stream(app_id="...", message="今天天氣？"):
        print(chunk, end="", flush=True)

    # 知識庫
    kbs = client.knowledge.list()
    docs = client.knowledge.documents(kb_id=kbs[0].id)

    # 用量 / quota
    summary = client.usage.summary()
"""
from .client import StaffKMClient
from .errors import StaffKMError, QuotaExceeded, AuthError

__all__ = ["StaffKMClient", "StaffKMError", "QuotaExceeded", "AuthError"]
__version__ = "0.1.0"
