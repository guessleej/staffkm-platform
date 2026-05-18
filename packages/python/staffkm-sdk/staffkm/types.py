"""Lightweight pydantic models for SDK responses.

Note: only the most common shapes are typed. Everything else is left as
``dict[str, Any]`` to avoid blocking on every server-side schema change.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class Workspace(BaseModel):
    id: str
    name: str
    slug: str | None = None


class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: str | None = None


class Application(BaseModel):
    id: str
    name: str
    type: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    content: str
    citations: list[dict[str, Any]] = []
    usage: dict[str, Any] | None = None


class QuotaSummary(BaseModel):
    monthly_token_cap: int | None = None
    monthly_cost_cap_usd: float | None = None
    tokens_used: int | None = None
    cost_used_usd: float | None = None
