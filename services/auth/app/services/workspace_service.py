"""Workspace + Member 的業務邏輯（RFC-001 Stage 2）。"""
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from staffkm_tenant.models import Workspace, WorkspaceMember, WorkspaceRole

log = structlog.get_logger()


class WorkspaceServiceError(HTTPException):
    pass


def _http(code: int, msg: str) -> WorkspaceServiceError:
    return WorkspaceServiceError(status_code=code, detail=msg)


class WorkspaceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Workspace 層 ────────────────────────────────────────────

    async def list_for_user(self, user_id: uuid.UUID) -> list[dict]:
        """回傳該 user 所屬的 workspace 清單，含其角色與成員數。"""
        stmt = (
            select(
                Workspace,
                WorkspaceMember.role,
                func.count(WorkspaceMember.id).over(partition_by=Workspace.id).label("member_count"),
            )
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_active == True,
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {**ws.__dict__, "role": role, "member_count": count}
            for ws, role, count in rows
        ]

    async def get(self, ws_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        """取得單一 workspace；user 必須是成員。"""
        ws, role, count = await self._get_with_role(ws_id, user_id)
        return {**ws.__dict__, "role": role, "member_count": count}

    async def create(
        self,
        name: str,
        slug: str,
        description: str | None,
        creator_id: uuid.UUID,
    ) -> Workspace:
        """建立 workspace；建立者自動成為 owner。"""
        # slug 唯一性檢查
        exists = await self.session.execute(
            select(Workspace.id).where(Workspace.slug == slug, Workspace.deleted_at.is_(None))
        )
        if exists.scalar_one_or_none():
            raise _http(status.HTTP_409_CONFLICT, f"workspace slug 已存在：{slug}")

        ws = Workspace(name=name, slug=slug, description=description)
        self.session.add(ws)
        await self.session.flush()

        # 自動加 owner
        member = WorkspaceMember(
            workspace_id=ws.id,
            user_id=creator_id,
            role=WorkspaceRole.OWNER.value,
            joined_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self.session.add(member)
        await self.session.commit()
        log.info("workspace_created", ws_id=str(ws.id), slug=slug, creator=str(creator_id))
        return ws

    async def update(
        self,
        ws_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Workspace:
        """編輯 workspace 名稱 / 描述（admin 以上可改）。"""
        ws, role, _ = await self._get_with_role(ws_id, user_id)
        if not WorkspaceRole(role).can_manage_members:
            raise _http(status.HTTP_403_FORBIDDEN, "需要 owner / admin 角色")
        if name is not None:
            ws.name = name
        if description is not None:
            ws.description = description
        await self.session.commit()
        log.info("workspace_updated", ws_id=str(ws_id), user=str(user_id))
        return ws

    async def soft_delete(self, ws_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """軟刪除（owner 限定）。"""
        ws, role, _ = await self._get_with_role(ws_id, user_id)
        if WorkspaceRole(role) != WorkspaceRole.OWNER:
            raise _http(status.HTTP_403_FORBIDDEN, "僅 owner 可刪除工作區")
        ws.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        log.warning("workspace_deleted", ws_id=str(ws_id), user=str(user_id))

    # ─── Member 層 ──────────────────────────────────────────────

    async def list_members(self, ws_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
        """列成員（任何成員都能看）。"""
        await self._get_with_role(ws_id, user_id)  # 權限檢查
        stmt = (
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == ws_id, WorkspaceMember.is_active == True)
            .order_by(WorkspaceMember.invited_at.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "user_id":      u.id,
                "username":     u.username,
                "display_name": u.display_name,
                "email":        u.email,
                "role":         m.role,
                "joined_at":    m.joined_at,
                "invited_at":   m.invited_at,
                "is_active":    m.is_active,
            }
            for m, u in rows
        ]

    async def invite(
        self,
        ws_id:        uuid.UUID,
        inviter_id:   uuid.UUID,
        invitee_id:   uuid.UUID,
        role:         str,
    ) -> WorkspaceMember:
        """邀請成員（admin 以上可邀；無 email 流程，假設 invitee 已是平台 user）。"""
        _, inviter_role, _ = await self._get_with_role(ws_id, inviter_id)
        if not WorkspaceRole(inviter_role).can_manage_members:
            raise _http(status.HTTP_403_FORBIDDEN, "需要 owner / admin 角色")

        # 不能邀請自己
        if invitee_id == inviter_id:
            raise _http(status.HTTP_400_BAD_REQUEST, "不能邀請自己")

        # 已是成員？
        existing = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.user_id == invitee_id,
            )
        )
        if existing.scalar_one_or_none():
            raise _http(status.HTTP_409_CONFLICT, "user 已是工作區成員")

        # 確認 invitee 存在
        user = await self.session.get(User, invitee_id)
        if not user:
            raise _http(status.HTTP_404_NOT_FOUND, "invitee user 不存在")

        member = WorkspaceMember(
            workspace_id=ws_id,
            user_id=invitee_id,
            role=role,
            invited_by=inviter_id,
            joined_at=datetime.now(timezone.utc),  # v0.1 直接生效，不做接受流程
            is_active=True,
        )
        self.session.add(member)
        await self.session.commit()
        log.info("workspace_member_added", ws_id=str(ws_id), user=str(invitee_id), role=role)
        return member

    async def update_role(
        self,
        ws_id:    uuid.UUID,
        actor_id: uuid.UUID,
        target_id: uuid.UUID,
        new_role: str,
    ) -> WorkspaceMember:
        """調整成員角色（admin/owner 可改；不能把自己降級為 viewer 以下，避免鎖死）。"""
        _, actor_role, _ = await self._get_with_role(ws_id, actor_id)
        if not WorkspaceRole(actor_role).can_manage_members:
            raise _http(status.HTTP_403_FORBIDDEN, "需要 owner / admin 角色")

        # 防止把最後一個 owner 降級
        if actor_id == target_id and WorkspaceRole(actor_role) == WorkspaceRole.OWNER \
                and new_role != WorkspaceRole.OWNER.value:
            owner_count = await self.session.scalar(
                select(func.count(WorkspaceMember.id)).where(
                    WorkspaceMember.workspace_id == ws_id,
                    WorkspaceMember.role == WorkspaceRole.OWNER.value,
                    WorkspaceMember.is_active == True,
                )
            )
            if (owner_count or 0) <= 1:
                raise _http(status.HTTP_400_BAD_REQUEST, "工作區至少要保留 1 名 owner")

        member = await self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.user_id == target_id,
            )
        )
        if not member:
            raise _http(status.HTTP_404_NOT_FOUND, "成員不存在")
        member.role = new_role
        await self.session.commit()
        log.info("workspace_member_role_changed", ws_id=str(ws_id), user=str(target_id), role=new_role)
        return member

    async def remove(self, ws_id: uuid.UUID, actor_id: uuid.UUID, target_id: uuid.UUID) -> None:
        """移除成員（admin/owner 可移）；soft delete via is_active=False。"""
        _, actor_role, _ = await self._get_with_role(ws_id, actor_id)
        if not WorkspaceRole(actor_role).can_manage_members:
            raise _http(status.HTTP_403_FORBIDDEN, "需要 owner / admin 角色")

        member = await self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.user_id == target_id,
            )
        )
        if not member:
            raise _http(status.HTTP_404_NOT_FOUND, "成員不存在")

        # 防止移除最後一個 owner
        if member.role == WorkspaceRole.OWNER.value:
            owner_count = await self.session.scalar(
                select(func.count(WorkspaceMember.id)).where(
                    WorkspaceMember.workspace_id == ws_id,
                    WorkspaceMember.role == WorkspaceRole.OWNER.value,
                    WorkspaceMember.is_active == True,
                )
            )
            if (owner_count or 0) <= 1:
                raise _http(status.HTTP_400_BAD_REQUEST, "不能移除最後一名 owner")

        member.is_active = False
        await self.session.commit()
        log.warning("workspace_member_removed", ws_id=str(ws_id), user=str(target_id))

    # ─── 內部 helper ─────────────────────────────────────────────

    async def _get_with_role(
        self, ws_id: uuid.UUID, user_id: uuid.UUID,
    ) -> tuple[Workspace, str, int]:
        """取 workspace + 呼叫者角色 + 成員總數；非成員 raise 403。"""
        stmt = (
            select(
                Workspace,
                WorkspaceMember.role,
                func.count(WorkspaceMember.id).over(partition_by=Workspace.id).label("member_count"),
            )
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                Workspace.id == ws_id,
                Workspace.deleted_at.is_(None),
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_active == True,
            )
        )
        row = (await self.session.execute(stmt)).first()
        if not row:
            raise _http(status.HTTP_403_FORBIDDEN, "您不是此工作區的成員，或工作區不存在")
        return row[0], row[1], row[2]
