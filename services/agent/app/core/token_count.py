"""Token 計算（Round 8-4）。

優先使用 tiktoken；未安裝時 fallback 到「字元 / 4」近似。

支援：
- count_text(text, model)         單一字串
- count_messages(messages, model) OpenAI Chat messages 結構（含 system/user/assistant）

選擇 encoding 規則：
- model 名含 'gpt-4o' / 'gpt-4.1' / 'o4' → o200k_base
- 'gpt-4' / 'gpt-3.5' → cl100k_base
- 'claude'*           → cl100k_base 作為近似（Anthropic 不公開 BPE；用最接近的）
- 'gemini'*           → cl100k_base 近似
- 其他               → cl100k_base 為通用回退
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import structlog

log = structlog.get_logger()


def _pick_encoding(model: str | None) -> str:
    m = (model or "").lower()
    if any(p in m for p in ("gpt-4o", "gpt-4.1", "o4", "o3")):
        return "o200k_base"
    return "cl100k_base"


@lru_cache(maxsize=8)
def _get_encoder(name: str):
    try:
        import tiktoken  # type: ignore
        return tiktoken.get_encoding(name)
    except ImportError:
        log.warning("tiktoken_not_installed", note="fallback to char/4 approximation")
        return None
    except Exception as e:
        log.warning("tiktoken_encoding_failed", name=name, error=str(e))
        return None


def count_text(text: str, *, model: str | None = None) -> int:
    """估算單一字串的 token 數。

    tiktoken 可用 → 精確；否則 char/4（中英文混合最穩近似）
    """
    if not text:
        return 0
    enc = _get_encoder(_pick_encoding(model))
    if enc is None:
        return max(1, len(text) // 4)
    return len(enc.encode(text))


def count_messages(messages: list[dict[str, Any]], *, model: str | None = None) -> int:
    """OpenAI Chat messages tokens 估算。

    使用簡化規則：每則訊息 + 4 tokens overhead（role + delimiter）；末尾再 +2 兼容
    primer。比 tiktoken 官方公式略寬，避免低估。
    """
    enc = _get_encoder(_pick_encoding(model))
    overhead_per_msg = 4
    n = 0
    for m in messages or []:
        content = m.get("content") or ""
        if not isinstance(content, str):
            content = str(content)
        if enc is None:
            n += overhead_per_msg + max(1, len(content) // 4)
        else:
            n += overhead_per_msg + len(enc.encode(content))
    return n + 2


def using_tiktoken() -> bool:
    """供前端 / metrics 判斷目前的計費是否精確。"""
    return _get_encoder("cl100k_base") is not None
