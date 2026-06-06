"""v5.13: 查詢改寫 / 多查詢展開（multi-query）。

問題：使用者 query 用詞常與文件用詞不同（同義詞、縮寫、口語），單一 query 向量召回有限。
做法：用地端 LLM 把 query 改寫成數個語意等價、用詞不同的變體 → 各自檢索 → RRF 融合。
原則：
- 任何失敗（LLM 不可達/空回/解析失敗）一律安全退回 [原query]，絕不阻斷檢索。
- 預設關（QUERY_EXPAND_ENABLED）：多 1 次 LLM + N 次 embedding，是品質換成本，由部署決定。
- 用 reasoning fallback（msg.content or reasoning_content），相容 thinking 型地端模型。
"""
from __future__ import annotations

import json
import re

import structlog
from openai import AsyncOpenAI

from app.config import settings

log = structlog.get_logger()

_SYS = (
    "你是檢索查詢改寫器。把使用者問題改寫成數個「語意等價、但用詞不同」的繁體中文查詢，"
    "涵蓋同義詞、展開縮寫、補關鍵詞，目的是提升向量檢索的召回。"
    "只輸出 JSON 字串陣列，例如 [\"改寫一\",\"改寫二\"]，不要任何解釋或編號。"
)


def _parse_list(raw: str) -> list[str]:
    """從 LLM 回應萃取字串清單：先試 JSON 陣列，再退回逐行。"""
    raw = (raw or "").strip()
    if not raw:
        return []
    # 去掉 ```json fence
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if m:
        try:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                return [str(x).strip() for x in arr if str(x).strip()]
        except Exception:  # noqa: BLE001
            pass
    # 逐行 fallback：去除項目符號 / 編號
    out = []
    for line in raw.splitlines():
        s = re.sub(r"^\s*(?:[-*•]|\d+[.)、])\s*", "", line).strip().strip('"').strip()
        if s:
            out.append(s)
    return out


async def expand_query(query: str, n: int | None = None) -> list[str]:
    """回 [原query] + 最多 n 個改寫。失敗一律退回 [原query]（去重、保序）。"""
    q = (query or "").strip()
    if not q:
        return []
    if not settings.QUERY_EXPAND_ENABLED:
        return [q]
    n = n or settings.QUERY_EXPAND_N
    try:
        client = AsyncOpenAI(
            api_key=settings.QUERY_EXPAND_API_KEY or "dummy",
            base_url=settings.QUERY_EXPAND_BASE_URL,
        )
        _ml = (settings.QUERY_EXPAND_MODEL or "").lower()
        temperature = 1 if ("kimi-k2" in _ml or _ml.startswith(("o1", "o3"))) else 0.3
        resp = await client.chat.completions.create(
            model=settings.QUERY_EXPAND_MODEL,
            messages=[
                {"role": "system", "content": _SYS},
                {"role": "user", "content": f"問題：{q}\n產生 {n} 個改寫。"},
            ],
            temperature=temperature,
            max_tokens=512,
            stream=False,
        )
        msg = resp.choices[0].message
        raw = msg.content or getattr(msg, "reasoning_content", "") or ""
        variants = _parse_list(raw)
    except Exception as e:  # noqa: BLE001
        log.warning("query_expand_failed", error=str(e)[:200])
        return [q]

    out = [q]
    for v in variants:
        v = v.strip()
        if v and v not in out:
            out.append(v)
        if len(out) >= n + 1:
            break
    log.info("query_expanded", original=q[:40], n_variants=len(out) - 1)
    return out
