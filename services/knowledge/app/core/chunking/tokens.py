"""Token 用量近似估計。

不接 tiktoken / sentencepiece 等重型依賴，以字符類型加權近似：
  - CJK 字符：≈ 1.5 token（含全形標點）
  - 英數字：≈ 0.3 token（以 4 chars/token 平均估計）
  - 空白 / 換行：忽略

此估計用於切片時粗略預算控制，避免送出超過 LLM context window 的 chunk。
"""
from .base import is_cjk


def approx_tokens(text: str) -> int:
    if not text:
        return 0
    cjk = ascii_chars = 0
    for ch in text:
        if ch.isspace():
            continue
        if is_cjk(ch):
            cjk += 1
        else:
            ascii_chars += 1
    return int(cjk * 1.5 + ascii_chars * 0.3)
