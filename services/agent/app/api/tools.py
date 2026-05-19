"""Tools API — 工具獨立模組（RFC-006 新 backlog）。

kind: http / mcp / shell / custom / workflow（v2.8 對齊 MaxKB workflow-type tool）
config: 依 kind 不同；http 例：{"url": "...", "method": "POST", "headers": {...}}

v2.8 擴充欄位（migration 0022）：
  - tool_type:      與 kind 同義，過渡期保留 kind；後續 UI 應切到 tool_type
  - application_id: tool_type='workflow' 時指向 applications.id
  - input_schema:   function-calling JSON schema
  - output_schema:  function-calling 回傳結構
  - code:           Python def run() 函式原碼（custom / AI 生成）

runtime（agent 對話 loop 把 workflow tool 當 callable function 給 LLM）
尚未完成 — 見 TODO in services/agent/app/core/application_agent.py。
"""
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api._generic_crud import make_crud_router
from app.config import settings
from staffkm_core.schemas.response import ApiResponse
from staffkm_tenant import TenantContext, require_writer


class ToolOut(BaseModel):
    id:           uuid.UUID
    workspace_id: uuid.UUID
    name:         str
    description:  str | None
    kind:         str
    config:       dict[str, Any]
    is_enabled:   bool
    created_at:   datetime
    updated_at:   datetime
    created_by:   uuid.UUID | None
    updated_by:   uuid.UUID | None
    # v2.8 新欄位（可能為 None 以相容舊資料）
    tool_type:      str | None = None
    application_id: uuid.UUID | None = None
    input_schema:   dict[str, Any] | None = None
    output_schema:  dict[str, Any] | None = None
    code:           str | None = None


class ToolCreate(BaseModel):
    name:        str = Field(..., max_length=128)
    description: str | None = None
    kind:        str = Field(default="http")
    config:      dict[str, Any] = Field(default_factory=dict)
    is_enabled:  bool = True
    # v2.8
    tool_type:      str | None = None
    application_id: uuid.UUID | None = None
    input_schema:   dict[str, Any] = Field(default_factory=dict)
    output_schema:  dict[str, Any] = Field(default_factory=dict)
    code:           str | None = None


class ToolUpdate(BaseModel):
    name:        str | None = Field(default=None, max_length=128)
    description: str | None = None
    kind:        str | None = None
    config:      dict[str, Any] | None = None
    is_enabled:  bool | None = None
    tool_type:      str | None = None
    application_id: uuid.UUID | None = None
    input_schema:   dict[str, Any] | None = None
    output_schema:  dict[str, Any] | None = None
    code:           str | None = None


router = make_crud_router(
    table="tools",
    out_model=ToolOut,
    create_model=ToolCreate,
    update_model=ToolUpdate,
    jsonb_fields=("config", "input_schema", "output_schema"),
)


# ─────────────────────────────────────────────────────────────────────
# v2.8 — AI 自動生成 Tool 程式碼
# ─────────────────────────────────────────────────────────────────────


class _Field(BaseModel):
    name:        str
    type:        str = "string"  # string|number|boolean|object|array
    description: str | None = None


class CodeGenRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=2000,
                             description="自然語言描述這個 tool 做什麼")
    inputs:  list[_Field] = Field(default_factory=list)
    outputs: list[_Field] = Field(default_factory=list)
    model:   str | None = None


class CodeGenResponse(BaseModel):
    code: str


_SYSTEM_PROMPT = """你是 staffKM tool 程式碼產生器。請依使用者的自然語言描述、輸入/輸出 schema，
產生符合下列規範的 Python 函式：

1. 必須命名為 `def run(**kwargs) -> dict:`
2. 從 kwargs 取出輸入欄位，做你的處理
3. return 一個 dict，key 對應 outputs 定義
4. 可以 `import` 標準函式庫；如需 HTTP 用 `import httpx`
5. 處理可能的例外，失敗時 `return {"error": "..."}`
6. **只輸出 Python 程式碼**，不要解釋、不要 markdown fence

範例：
描述：把攝氏溫度轉華氏
inputs: [{"name": "celsius", "type": "number"}]
outputs: [{"name": "fahrenheit", "type": "number"}]

輸出：
def run(**kwargs) -> dict:
    c = float(kwargs.get("celsius", 0))
    return {"fahrenheit": c * 9 / 5 + 32}
"""


def _extract_code(text: str) -> str:
    """從 LLM response 抓 Python code（容錯 markdown code fence）。"""
    import re
    m = re.search(r"```(?:python)?\s*(.+?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


@router.post(
    "/generate-code",
    response_model=ApiResponse[CodeGenResponse],
    summary="AI 自動生成 Tool 程式碼（v2.8）",
)
async def generate_code(
    body: CodeGenRequest,
    ctx: TenantContext = Depends(require_writer),
):
    import httpx

    api_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY
    base_url = (
        "https://api.openai.com/v1"
        if "openai" in settings.LLM_PROVIDER.lower()
        else settings.LLM_BASE_URL
    )
    model = body.model or settings.LLM_MODEL
    if not api_key:
        raise HTTPException(503, "LLM 未設定（請填入 OPENAI_API_KEY 或 LLM_API_KEY）")

    user_prompt = (
        f"描述：{body.description}\n"
        f"inputs: {[i.model_dump() for i in body.inputs]}\n"
        f"outputs: {[o.model_dump() for o in body.outputs]}\n"
        "請輸出 Python 程式碼："
    )
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1500,
                },
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(502, f"LLM 呼叫失敗：{e}")

    return ApiResponse(data=CodeGenResponse(code=_extract_code(raw)))
