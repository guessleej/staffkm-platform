"""API key 加密層單元測試（Round 8-3 fernet + plain/legacy fallback；安全相關、原本無守）。

非 fernet 路徑（plain:/legacy/round-trip-no-key）為「金鑰未設時的儲存正確性」核心，
不需 cryptography → 一律跑。fernet 路徑用 importorskip 守。
"""
from __future__ import annotations

import base64
import importlib
import sys
from pathlib import Path

import pytest

_SVC = Path(__file__).resolve().parent.parent  # services/agent
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))


def _fresh_secrets(monkeypatch, key: str | None):
    """重載 secrets 模組並重置 fernet cache（避免跨測試污染）。"""
    if key is None:
        monkeypatch.delenv("STAFFKM_SECRETS_KEY", raising=False)
    else:
        monkeypatch.setenv("STAFFKM_SECRETS_KEY", key)
    import app.core.secrets as secrets  # noqa: E402
    importlib.reload(secrets)
    return secrets


def test_decrypt_none_and_empty(monkeypatch):
    s = _fresh_secrets(monkeypatch, None)
    assert s.decrypt_secret(None) is None
    assert s.decrypt_secret("") is None
    assert s.encrypt_secret(None) is None
    assert s.encrypt_secret("") is None


def test_plain_prefix_roundtrip_without_key(monkeypatch):
    s = _fresh_secrets(monkeypatch, None)  # 無金鑰 → encrypt 走 plain:
    enc = s.encrypt_secret("sk-abc123")
    assert enc == "plain:sk-abc123"
    assert s.decrypt_secret(enc) == "sk-abc123"


def test_decrypt_plain_prefix(monkeypatch):
    s = _fresh_secrets(monkeypatch, None)
    assert s.decrypt_secret("plain:hello") == "hello"


def test_legacy_base64(monkeypatch):
    s = _fresh_secrets(monkeypatch, None)
    b64 = base64.b64encode("legacy-key".encode()).decode()
    assert s.decrypt_secret(b64) == "legacy-key"          # 可解 + printable → 用解碼值


def test_legacy_plaintext_passthrough(monkeypatch):
    s = _fresh_secrets(monkeypatch, None)
    # 非 base64 / 解出非 printable → 當原文回傳
    assert s.decrypt_secret("not!!base64@@plain") == "not!!base64@@plain"


def test_fernet_roundtrip(monkeypatch):
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet
    s = _fresh_secrets(monkeypatch, Fernet.generate_key().decode())
    enc = s.encrypt_secret("super-secret-key")
    assert enc.startswith("fernet:")
    assert s.decrypt_secret(enc) == "super-secret-key"
