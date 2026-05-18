"""Worker backend status admin API (v4.0 P3/P4)。

提供：
- GET /backend → 目前 WORKER_BACKEND (inprocess | arq)
- GET /queue   → arq backend 下 Redis queue 深度（inprocess 回 None）

admin 角色限定（讀 X-User-Roles header；跟 admin_billing / heartbeats 同 pattern）。
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request

from staffkm_core.schemas.response import ApiResponse

router = APIRouter()


def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="admin only")


@router.get("/backend", response_model=ApiResponse, summary="目前 worker backend (inprocess|arq)")
async def get_backend(request: Request):
    _require_admin(request)
    backend = os.environ.get("WORKER_BACKEND", "inprocess").strip().lower()
    return ApiResponse(data={"backend": backend})


@router.get("/queue", response_model=ApiResponse, summary="arq queue depth (Redis zset)")
async def get_queue_depth(request: Request):
    _require_admin(request)
    backend = os.environ.get("WORKER_BACKEND", "inprocess").strip().lower()
    if backend != "arq":
        return ApiResponse(data={
            "backend": backend,
            "queue_depth": None,
            "note": "arq backend not enabled",
        })
    try:
        from arq.connections import create_pool

        from staffkm_core.utils.arq_settings import REDIS_SETTINGS
        pool = await create_pool(REDIS_SETTINGS)
        try:
            depth = await pool.zcard("arq:queue")
            return ApiResponse(data={"backend": "arq", "queue_depth": int(depth or 0)})
        finally:
            await pool.aclose()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"queue query failed: {e}")
