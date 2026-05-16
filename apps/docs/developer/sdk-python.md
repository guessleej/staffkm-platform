# Python SDK

```bash
pip install staffkm-sdk
```

## 基本

```python
from staffkm_sdk import StaffKMClient

client = StaffKMClient(
    base_url="https://staffkm.example.com",
    api_key="sk-...",
    workspace_id="...",
)
```

## Chat

```python
# 一次性
resp = client.chat(app_id="...", message="今天天氣？")
print(resp.content)
for c in resp.citations:
    print(c["doc_name"])

# SSE 串流
for chunk in client.chat_stream(app_id="...", message="今天天氣？"):
    print(chunk, end="", flush=True)
```

## 其他

```python
# 應用 / 知識庫 / 用量
apps   = client.apps.list()
kbs    = client.knowledge.list()
docs   = client.knowledge.documents(kb_id=kbs[0]["id"])
hits   = client.knowledge.search(kb_id=kbs[0]["id"], query="請假流程", top_k=5)

usage  = client.usage.summary()       # 當月 tokens / cost / requests
logs   = client.usage.logs()
quota  = client.usage.quota()
client.usage.set_quota(monthly_token_cap=5_000_000, monthly_cost_cap_usd=200)
```

## Context manager

```python
with StaffKMClient(...) as c:
    print(c.chat(app_id="...", message="…").content)
# 自動關 httpx 連線池
```

## 錯誤處理

```python
from staffkm_sdk import StaffKMClient, AuthError, QuotaExceeded, StaffKMError

try:
    c.chat(app_id="...", message="...")
except QuotaExceeded as e:
    print("超額：", e)
except AuthError:
    print("api key 失效")
except StaffKMError as e:
    print("api error", e.status_code, e.detail)
```
