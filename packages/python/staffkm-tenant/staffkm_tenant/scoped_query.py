"""WorkspaceScopedQuery — 自動把 workspace_id filter 套到所有業務 query。

設計目的：把「跨 workspace 漏查」風險從「靠人記得加 filter」變成「靠類型/lint 強制」。

用法：
    from staffkm_tenant import WorkspaceScopedQuery
    from app.models import KnowledgeBase

    # ✅ 安全：自動帶 workspace_id
    q = WorkspaceScopedQuery(KnowledgeBase).select()
    result = await session.execute(q)

    # ✅ 還能加額外條件
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.is_public == True)

    # ❌ 禁止：直接 select(KnowledgeBase) — lint rule 會擋
"""
from typing import TypeVar, Generic
from sqlalchemy import Select, select, delete, update
from sqlalchemy.orm import DeclarativeBase

from staffkm_tenant.context import get_tenant_context

T = TypeVar("T", bound=DeclarativeBase)


class WorkspaceScopedQuery(Generic[T]):
    """所有業務 query 的入口；強制注入 workspace_id where clause。"""

    def __init__(self, model: type[T]):
        if not hasattr(model, "workspace_id"):
            raise TypeError(
                f"{model.__name__} 沒有 workspace_id 欄位，不應使用 WorkspaceScopedQuery。"
                "（若是全域資源如 User、Workspace 本身，請用一般 select。）"
            )
        self.model = model

    def _ws_filter(self):
        ctx = get_tenant_context()
        if ctx.is_system:
            # superadmin 可跨 workspace；通常 admin endpoints 才用
            return None
        return self.model.workspace_id == ctx.workspace_id

    def select(self) -> Select[tuple[T]]:
        stmt = select(self.model)
        f = self._ws_filter()
        return stmt.where(f) if f is not None else stmt

    def delete(self):
        stmt = delete(self.model)
        f = self._ws_filter()
        return stmt.where(f) if f is not None else stmt

    def update(self):
        stmt = update(self.model)
        f = self._ws_filter()
        return stmt.where(f) if f is not None else stmt
