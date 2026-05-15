"""FastAPI middleware — 從 URL path 取出 workspace_id，驗證成員資格，注入 context。"""
import re
import uuid
import structlog
from typing import Awaitable, Callable

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from staffkm_tenant.context import TenantContext, set_tenant_context, clear_tenant_context
from staffkm_tenant.models import WorkspaceMember, WorkspaceRole

log = structlog.get_logger()

# /api/v1/workspace/{ws_id}/...   → 抓 ws_id
_WORKSPACE_PATH_RE = re.compile(r"/workspace/([0-9a-f-]{36})/")


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    使用方式：
        app.add_middleware(
            TenantContextMiddleware,
            session_factory=session_factory,        # async_sessionmaker
            user_id_getter=lambda req: req.state.user_id,  # 從 auth middleware 拿
        )

    流程：
      1. 從 URL 抓 workspace_id（沒有就 pass，留給非 workspace-scoped endpoints）
      2. 查 workspace_member 確認 user 是成員
      3. 把 TenantContext 注入 ContextVar
      4. 請求結束後 clear（避免汙染下個 request）
    """

    def __init__(
        self,
        app,
        session_factory: async_sessionmaker,
        user_id_getter: Callable[[Request], uuid.UUID | None],
    ):
        super().__init__(app)
        self.session_factory = session_factory
        self.get_user_id = user_id_getter

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        ws_match = _WORKSPACE_PATH_RE.search(request.url.path)
        if not ws_match:
            # 不是 workspace-scoped endpoint（如 /auth/login）→ 直接 pass
            return await call_next(request)

        ws_id_str = ws_match.group(1)
        try:
            workspace_id = uuid.UUID(ws_id_str)
        except ValueError:
            return JSONResponse(
                {"error": "invalid_workspace_id", "detail": ws_id_str},
                status_code=400,
            )

        user_id = self.get_user_id(request)
        if user_id is None:
            return JSONResponse({"error": "unauthenticated"}, status_code=401)

        # 查成員資格
        async with self.session_factory() as session:
            stmt = select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_active == True,
            )
            result = await session.execute(stmt)
            member = result.scalar_one_or_none()

        if member is None:
            log.warning(
                "tenant_access_denied",
                workspace_id=str(workspace_id),
                user_id=str(user_id),
                path=request.url.path,
            )
            return JSONResponse(
                {"error": "forbidden", "detail": "not a member of workspace"},
                status_code=403,
            )

        ctx = TenantContext(
            workspace_id=workspace_id,
            user_id=user_id,
            role=WorkspaceRole(member.role),
        )
        set_tenant_context(ctx)
        # 也把 ctx 放 request.state 方便 dependency 取用
        request.state.tenant = ctx

        try:
            return await call_next(request)
        finally:
            clear_tenant_context()
