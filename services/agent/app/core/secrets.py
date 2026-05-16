"""API Key 加密層（Round 8-3 — fernet）。

設計：
- 使用 Fernet 對稱加密（AES-128-CBC + HMAC-SHA256）
- 主金鑰由環境變數 STAFFKM_SECRETS_KEY 提供（base64-urlsafe 32 bytes）
- 未設定金鑰或 cryptography 未安裝 → fallback 到 base64 編碼（明確 log warning）
- 自動偵測既有 base64 / 明文格式 → 解密 / 透傳，向後相容

DB 欄位（`model_providers.api_key_enc`）儲存格式：
- 真正加密：`fernet:gAAAAA...`
- 仍是明文（legacy）：`plain:sk-xxx`
- base64 (legacy)：直接 base64 字串（無 prefix）

caller：
    from app.core.secrets import encrypt_secret, decrypt_secret
    enc = encrypt_secret("sk-xxxx")           # 寫入 DB
    plain = decrypt_secret(enc)               # 讀取使用

加密金鑰產生：
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations

import base64
import os

import structlog

log = structlog.get_logger()

_FERNET = None
_FERNET_INITED = False
_PREFIX_FERNET = "fernet:"
_PREFIX_PLAIN  = "plain:"


def _get_fernet():
    """lazy-load fernet；金鑰未設或 cryptography 未裝時回 None。"""
    global _FERNET, _FERNET_INITED
    if _FERNET_INITED:
        return _FERNET
    _FERNET_INITED = True

    key = os.environ.get("STAFFKM_SECRETS_KEY")
    if not key:
        log.warning(
            "secrets_no_key",
            note="STAFFKM_SECRETS_KEY 未設定；API key 將以 plain: 前綴儲存（無加密）。",
        )
        return None

    try:
        from cryptography.fernet import Fernet  # type: ignore
        _FERNET = Fernet(key.encode() if isinstance(key, str) else key)
    except ImportError:
        log.warning("secrets_no_cryptography",
                    note="cryptography 未安裝；fallback 到 plain:")
        _FERNET = None
    except Exception as e:
        log.warning("secrets_key_invalid", error=str(e))
        _FERNET = None
    return _FERNET


def encrypt_secret(plain: str | None) -> str | None:
    """加密 + 標記前綴；plain 為空回 None。"""
    if not plain:
        return None
    f = _get_fernet()
    if f is None:
        return _PREFIX_PLAIN + plain
    token = f.encrypt(plain.encode("utf-8")).decode("ascii")
    return _PREFIX_FERNET + token


def decrypt_secret(enc: str | None) -> str | None:
    """依前綴自動 dispatch；None / 空字串回 None。"""
    if not enc:
        return None
    if enc.startswith(_PREFIX_FERNET):
        f = _get_fernet()
        if f is None:
            log.warning("secrets_decrypt_no_key", note="DB 有加密文字但金鑰未設")
            return None
        try:
            return f.decrypt(enc[len(_PREFIX_FERNET):].encode("ascii")).decode("utf-8")
        except Exception as e:
            log.warning("secrets_decrypt_failed", error=str(e))
            return None
    if enc.startswith(_PREFIX_PLAIN):
        return enc[len(_PREFIX_PLAIN):]
    # legacy：無前綴。先嘗試 base64 解碼；失敗則當成明文
    try:
        decoded = base64.b64decode(enc.encode("ascii"), validate=False).decode("utf-8")
        # 若解碼結果看起來像 key（沒有控制字元），用之；否則當原文
        if decoded.isprintable():
            return decoded
    except Exception:
        pass
    return enc
