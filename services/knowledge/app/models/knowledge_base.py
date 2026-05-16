"""知識庫資料模型"""
import uuid
from enum import Enum

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any, Optional

from staffkm_core.models.base import Base, UUIDPrimaryKeyMixin, AuditMixin


class KBStatus(str, Enum):
    ACTIVE = "active"
    BUILDING = "building"
    ERROR = "error"
    DISABLED = "disabled"


class KnowledgeBase(Base, UUIDPrimaryKeyMixin, AuditMixin):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        Index("idx_knowledge_bases_workspace", "workspace_id"),
    )

    # ── 多租戶歸屬（RFC-001 Stage 2）— DB column 已由 0001 migration 建好 ──
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=True,    # Stage 2 過渡期 nullable；Stage 3 改 NOT NULL
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=KBStatus.ACTIVE)
    embedding_model: Mapped[str] = mapped_column(String(64), default="text-embedding-3-small")
    vector_store_type: Mapped[str] = mapped_column(String(32), default="pgvector")
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    tenant_id: Mapped[str | None] = mapped_column(String(64))   # legacy；下版移除

    # ── 切片策略（RFC-006 切片技術升級）─────────────────────────────
    chunk_strategy: Mapped[str] = mapped_column(String(16), default="auto")
    chunk_size:     Mapped[int] = mapped_column(default=512)
    chunk_overlap:  Mapped[int] = mapped_column(default=64)

    documents: Mapped[list["Document"]] = relationship(back_populates="knowledge_base", cascade="all, delete-orphan")


class DocStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Document(Base, UUIDPrimaryKeyMixin, AuditMixin):
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_workspace", "workspace_id"),
    )

    # ── 多租戶歸屬（RFC-001 Stage 2）──
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=True,
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default=DocStatus.PENDING)
    paragraph_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    paragraphs: Mapped[list["Paragraph"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Paragraph(Base, UUIDPrimaryKeyMixin, AuditMixin):
    __tablename__ = "paragraphs"
    __table_args__ = (
        Index("idx_paragraphs_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_paragraphs_workspace", "workspace_id"),
    )

    # ── 多租戶歸屬（RFC-001 Stage 2）──
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=True,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(256))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    # 預計算的 tsvector，供 FTS 使用（CJK 分字後以 simple 字典索引）
    search_vector: Mapped[Optional[Any]] = mapped_column(TSVECTOR, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="paragraphs")
