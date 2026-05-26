"""Auth 核心 service 層整合測試（真 PostgreSQL）。

守的是「登入大門」：`app.core.auth_service.AuthService` 的本地帳號驗證 +
JWT token 簽發。原本零守護——純邏輯單元無法涵蓋：
- bcrypt verify 對真 password_hash 的 round-trip
- 帳號狀態（active/inactive/locked）對登入的影響
- 不存在的帳號 / 錯密碼 → 一律 None（不可洩漏哪個錯）
- JWT access/refresh 的 claims（sub/username/roles/type）與 expiry

LDAP/AD 雙軌（`_ldap_authenticate_and_sync`）需真 AD server，CI 不可測 →
原始碼標 `# pragma: no cover`；本檔只測「ldap_dn 使用者在無 AD 時 bind 失敗 → None」
的 fail-safe 路徑（ldap3 未裝會 ImportError → 同樣回 False，安全）。
"""
from __future__ import annotations

import uuid

import jwt
import pytest

from app.config import settings
from app.core.auth_service import AuthService, pwd_ctx
from app.models.user import User, UserStatus

pytestmark = pytest.mark.asyncio


async def _seed_user(session, *, username="alice", password="s3cret!", status=UserStatus.ACTIVE,
                     roles=None, ldap_dn=None, tenant_id=None) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        display_name=username.title(),
        password_hash=pwd_ctx.hash(password) if password else None,
        status=status,
        roles=roles if roles is not None else ["user"],
        ldap_dn=ldap_dn,
        tenant_id=tenant_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ── 本地帳號驗證 ─────────────────────────────────────────────────────────
async def test_authenticate_success(db_session):
    await _seed_user(db_session, username="alice", password="s3cret!")
    svc = AuthService(db_session)
    user = await svc.authenticate("alice", "s3cret!")
    assert user is not None
    assert user.username == "alice"


async def test_authenticate_wrong_password_returns_none(db_session):
    await _seed_user(db_session, username="bob", password="correct-horse")
    svc = AuthService(db_session)
    assert await svc.authenticate("bob", "wrong") is None


async def test_authenticate_unknown_user_returns_none(db_session):
    svc = AuthService(db_session)
    assert await svc.authenticate("ghost", "whatever") is None


async def test_authenticate_inactive_account_blocked(db_session):
    await _seed_user(db_session, username="carol", password="pw", status=UserStatus.INACTIVE)
    svc = AuthService(db_session)
    assert await svc.authenticate("carol", "pw") is None


async def test_authenticate_locked_account_blocked(db_session):
    await _seed_user(db_session, username="dave", password="pw", status=UserStatus.LOCKED)
    svc = AuthService(db_session)
    assert await svc.authenticate("dave", "pw") is None


async def test_authenticate_empty_password_hash_returns_none(db_session):
    """password_hash 為 NULL（如純 SSO 帳號）→ 本地密碼驗證一律失敗（不可空密碼登入）。"""
    await _seed_user(db_session, username="erin", password=None)
    svc = AuthService(db_session)
    assert await svc.authenticate("erin", "") is None
    assert await svc.authenticate("erin", "anything") is None


async def test_ldap_user_without_server_fails_safe(db_session):
    """ldap_dn 使用者但 AD 不可達（或 ldap3 未裝）→ _ldap_bind False → None（fail-safe）。"""
    await _seed_user(db_session, username="frank", password=None,
                     ldap_dn="cn=frank,dc=example,dc=com")
    svc = AuthService(db_session)
    assert await svc.authenticate("frank", "pw") is None


# ── JWT token 簽發 ───────────────────────────────────────────────────────
async def test_generate_tokens_claims(db_session):
    user = await _seed_user(db_session, username="grace", roles=["user", "admin"], tenant_id="t-1")
    svc = AuthService(db_session)
    tokens = svc.generate_tokens(user)

    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == settings.JWT_EXPIRE_MINUTES * 60

    access = jwt.decode(tokens["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert access["sub"] == str(user.id)
    assert access["username"] == "grace"
    assert access["roles"] == ["user", "admin"]
    assert access["tenant_id"] == "t-1"
    assert "exp" in access and "iat" in access

    refresh = jwt.decode(tokens["refresh_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert refresh["sub"] == str(user.id)
    assert refresh["type"] == "refresh"


async def test_access_token_rejects_wrong_secret(db_session):
    user = await _seed_user(db_session, username="heidi")
    svc = AuthService(db_session)
    tokens = svc.generate_tokens(user)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(tokens["access_token"], "not-the-secret", algorithms=["HS256"])


async def test_authenticate_then_issue_tokens_roundtrip(db_session):
    """端到端：seed → authenticate → generate_tokens → decode 一致。"""
    seeded = await _seed_user(db_session, username="ivan", password="pa55", roles=["user"])
    svc = AuthService(db_session)
    user = await svc.authenticate("ivan", "pa55")
    assert user is not None
    tokens = svc.generate_tokens(user)
    decoded = jwt.decode(tokens["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert decoded["sub"] == str(seeded.id)
