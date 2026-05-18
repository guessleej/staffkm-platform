"""Starter pack install — v4.1 A。

Admin-only endpoints。讀 image 內 /app/tools/starter-pack/*.json，
一鍵建 application + workflow_nodes + workflow_edges 到 caller 的 workspace。

注意：應用建立沿用 applications table 既有欄位（包含 workflow_manager 等）；
nodes/edges 寫進 workflow_nodes / workflow_edges（agent service 真實 schema，
非 spec 文件中的 application_nodes / application_edges）。
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Path as FPath
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()

# Container layout：Dockerfile COPY tools/starter-pack → /app/tools/starter-pack
STARTER_PACK_DIR = Path("/app/tools/starter-pack")
# dev fallback（uvicorn 本機跑 cwd=services/agent → 找 repo root 的 tools）
_DEV_FALLBACK = Path(__file__).resolve().parents[4] / "tools" / "starter-pack"


def _pack_dir() -> Path:
    if STARTER_PACK_DIR.exists():
        return STARTER_PACK_DIR
    return _DEV_FALLBACK


def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", None) or []
    if "admin" not in roles:
        raise HTTPException(403, "admin only")


@router.get("", response_model=ApiResponse, summary="列出可用 starter packs")
async def list_packs(request: Request):
    _require_admin(request)
    packs = []
    base = _pack_dir()
    if base.exists():
        for f in sorted(base.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                packs.append({
                    "id": f.stem,
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "icon": data.get("icon", "package"),
                })
            except Exception:
                continue
    return ApiResponse(data={"packs": packs})


@router.post("/{pack_id}/install", response_model=ApiResponse, summary="安裝 pack 到 caller 的 workspace")
async def install_pack(
    request: Request,
    pack_id: str = FPath(...),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    ws_id = request.headers.get("x-workspace-id") or request.headers.get("X-Workspace-ID")
    if not ws_id:
        raise HTTPException(400, "X-Workspace-ID header required")

    pack_file = _pack_dir() / f"{pack_id}.json"
    if not pack_file.exists():
        raise HTTPException(404, f"pack {pack_id} not found")
    data = json.loads(pack_file.read_text(encoding="utf-8"))

    app_id = str(uuid.uuid4())
    now = datetime.utcnow()
    user_id = getattr(request.state, "user_id", None)

    # 1. INSERT application（對齊 applications.py 真實欄位）
    await session.execute(text("""
        INSERT INTO applications (
            id, workspace_id, name, description, icon, type, status,
            system_prompt, welcome_message,
            suggested_questions, knowledge_base_ids, skill_ids, config,
            is_public, workflow_manager,
            created_at, updated_at, created_by
        ) VALUES (
            :id, :ws, :name, :desc, :icon, :type, 'active',
            :sp, :wm,
            CAST(:sq AS jsonb), CAST('[]' AS jsonb), CAST('[]' AS jsonb), CAST('{}' AS jsonb),
            FALSE, 'workflow',
            :now, :now, :uid
        )
    """), {
        "id": app_id, "ws": ws_id,
        "name": data["name"], "desc": data.get("description", ""),
        "icon": data.get("icon", "package"),
        "type": data.get("type", "knowledge-chat"),
        "sp": data.get("system_prompt", ""),
        "wm": data.get("welcome_message", ""),
        "sq": json.dumps(data.get("suggested_questions", []), ensure_ascii=False),
        "now": now, "uid": user_id,
    })

    # 2. INSERT workflow_nodes
    for n in data.get("nodes", []):
        await session.execute(text("""
            INSERT INTO workflow_nodes (
                id, application_id, workspace_id, node_type, node_key,
                label, config, position
            ) VALUES (
                :id, :app, :ws, :t, :k, :lbl, CAST(:c AS jsonb), CAST(:p AS jsonb)
            )
            ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid.uuid4()), "app": app_id, "ws": ws_id,
            "t": n.get("node_type", "start"),
            "k": n["node_key"],
            "lbl": n.get("label", ""),
            "c": json.dumps(n.get("config", {}), ensure_ascii=False),
            "p": json.dumps(n.get("position", {"x": 0, "y": 0}), ensure_ascii=False),
        })

    # 3. INSERT workflow_edges
    for e in data.get("edges", []):
        await session.execute(text("""
            INSERT INTO workflow_edges (
                id, application_id, workspace_id, source_node_key, target_node_key, condition
            ) VALUES (
                :id, :app, :ws, :s, :t, NULL
            )
            ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid.uuid4()), "app": app_id, "ws": ws_id,
            "s": e["source_node_key"], "t": e["target_node_key"],
        })

    await session.commit()
    return ApiResponse(
        data={"application_id": app_id, "name": data["name"], "pack_id": pack_id},
        message=f"installed: {data['name']}",
    )
