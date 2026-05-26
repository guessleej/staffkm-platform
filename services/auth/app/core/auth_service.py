"""身分驗證核心服務 — 本地帳號 + LDAP/AD 雙軌驗證 (使用 ldap3)"""
import datetime
import uuid

import jwt
import structlog
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserStatus

log = structlog.get_logger()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def authenticate(self, username: str, password: str) -> User | None:
        user = await self._get_user_by_username(username)

        if user:
            if user.status != UserStatus.ACTIVE:
                log.warning("login_disabled_account", username=username)
                return None
            if user.ldap_dn:
                if not self._ldap_bind(user.ldap_dn, password):
                    return None
            else:
                # password_hash 為 NULL（純 SSO/OIDC 帳號）→ 不可本地密碼登入。
                # 直接 deny，不丟給 pwd_ctx.verify("")（會 raise UnknownHashError → 500）。
                if not user.password_hash or not pwd_ctx.verify(password, user.password_hash):
                    return None
            return user

        if settings.LDAP_ENABLED:  # pragma: no cover  （LDAP fallback：需 live AD）
            return await self._ldap_authenticate_and_sync(username, password)

        return None

    async def _get_user_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    def _ldap_bind(self, dn: str, password: str) -> bool:
        try:
            from ldap3 import Server, Connection, ALL
            server = Server(settings.LDAP_SERVER, get_info=ALL)
            conn = Connection(server, user=dn, password=password)
            result = conn.bind()
            conn.unbind()
            return result
        except Exception as e:
            log.warning("ldap_bind_failed", dn=dn, error=str(e))
            return False

    async def _ldap_authenticate_and_sync(self, username: str, password: str) -> User | None:  # pragma: no cover
        # LDAP/AD 同步：需真 AD server，CI 無法整合測試（見 tests/integration/auth）。
        try:
            from ldap3 import Server, Connection, ALL, SUBTREE
            server = Server(settings.LDAP_SERVER, get_info=ALL)
            conn = Connection(server, user=settings.LDAP_BIND_DN, password=settings.LDAP_BIND_PASSWORD)
            if not conn.bind():
                return None

            conn.search(
                search_base=settings.LDAP_BASE_DN,
                search_filter=f"(sAMAccountName={username})",
                search_scope=SUBTREE,
                attributes=["mail", "displayName", "department"],
            )
            if not conn.entries:
                conn.unbind()
                return None

            entry = conn.entries[0]
            dn = entry.entry_dn
            conn.unbind()

            if not self._ldap_bind(dn, password):
                return None

            email = str(entry.mail.value) if entry.mail else ""
            display_name = str(entry.displayName.value) if entry.displayName else username
            department = str(entry.department.value) if entry.department else ""

            user = User(
                username=username,
                email=email,
                display_name=display_name,
                department=department,
                ldap_dn=dn,
                status=UserStatus.ACTIVE,
            )
            self.session.add(user)
            await self.session.flush()
            log.info("ldap_user_synced", username=username)
            return user

        except Exception as e:
            log.error("ldap_auth_failed", username=username, error=str(e))
            return None

    def generate_tokens(self, user: User) -> dict:
        now = datetime.datetime.now(datetime.timezone.utc)
        access_payload = {
            "sub": str(user.id),
            "username": user.username,
            "roles": user.roles,
            "tenant_id": user.tenant_id,
            "iat": now,
            "exp": now + datetime.timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        }
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "iat": now,
            "exp": now + datetime.timedelta(days=settings.REFRESH_TOKEN_DAYS),
        }
        return {
            "access_token": jwt.encode(access_payload, settings.SECRET_KEY, algorithm="HS256"),
            "refresh_token": jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm="HS256"),
            "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        }
