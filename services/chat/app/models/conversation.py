"""對話 Session 與訊息資料模型"""
import uuid

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from staffkm_core.models.base import Base, UUIDPrimaryKeyMixin, AuditMixin


class Conversation(Base, UUIDPrimaryKeyMixin, AuditMixin):
    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # v5.10.14：對話可綁 scenario（代理人）或 application（應用），二擇一 → 統一進「對話」
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(256))
    kb_ids: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[str | None] = mapped_column(String(64))
    # v2.7：分享對話紀錄（公開唯讀，無 token 為私密）
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base, UUIDPrimaryKeyMixin, AuditMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
