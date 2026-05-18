# staffkm-sdk (Python)

Official Python SDK for the staffKM platform.

> v0.2 (v4.5 Theme E) ships a new top-level `staffkm` module covering
> auth / workspaces / knowledge / applications / chat (stream) / quota /
> billing / plugins. The legacy `staffkm_sdk` package is still importable
> for backwards compatibility.

## Install

```bash
pip install -e packages/python/staffkm-sdk
```

## Quick start

```python
from staffkm import StaffKM

client = StaffKM(
    base_url="https://staffkm.example.com",
    api_key="sk_xxx",
    workspace_id="ws_abc",
)

# Non-streaming chat
res = client.chat.send(application_id="app_123", message="hello")
print(res)

# Streaming
for token in client.chat.stream(application_id="app_123", message="tell me a joke"):
    print(token, end="", flush=True)

# Knowledge base
kbs = client.knowledge.kbs.list()
hits = client.knowledge.hit_test(kb_id=kbs[0]["id"], query="退休金")
```

## Examples

- `examples/chat_streaming.py`
- `examples/upload_doc.py`
- `examples/bulk_eval.py`

## Exposed resources

| Resource | Methods |
|---|---|
| `auth` | login, refresh, me |
| `workspaces` | list, create, get |
| `knowledge` | kbs.list/create, docs.upload, hit_test |
| `applications` | list, create, get, run |
| `chat` | send, stream |
| `quota` | summary, set, list |
| `billing` | users.list, users.detail, users.csv |
| `plugins` | list, reload |

See `docs/dev/sdks.md` for the cross-language overview.
