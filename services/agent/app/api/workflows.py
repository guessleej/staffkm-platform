"""Workflow API — 管理 application 的 workflow 節點與執行"""
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.workflow.executor import WorkflowExecutor
from core.schemas.response import ApiResponse
from core.utils.database import get_session

router = APIRouter()


# ── Pydantic Schemas ────────────────────────────────────────────────────────


class WorkflowNode(BaseModel):
    id: str = ""
    node_key: str = ""
    node_type: str
    label: str = ""
    config: dict[str, Any] = {}
    position: dict[str, float] = {"x": 0, "y": 0}


class WorkflowEdge(BaseModel):
    id: str = ""
    source_node_key: str
    target_node_key: str
    condition: Any = None


class WorkflowSave(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class WorkflowChatRequest(BaseModel):
    user_input: str
    session_id: str = ""


# ── 取得工作流程 ────────────────────────────────────────────────────────────


@router.get(
    "/{app_id}/workflow",
    response_model=ApiResponse,
    summary="取得 Application 的工作流程",
)
async def get_workflow(
    app_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    nodes_rows = await session.execute(
        text(
            "SELECT * FROM workflow_nodes WHERE application_id = :app_id ORDER BY created_at"
        ),
        {"app_id": str(app_id)},
    )
    edges_rows = await session.execute(
        text("SELECT * FROM workflow_edges WHERE application_id = :app_id"),
        {"app_id": str(app_id)},
    )
    nodes = [dict(r._mapping) for r in nodes_rows.fetchall()]
    edges = [dict(r._mapping) for r in edges_rows.fetchall()]

    # 確保 config 是 dict
    for n in nodes:
        if isinstance(n.get("config"), str):
            n["config"] = json.loads(n["config"])
        # position 已是 JSONB dict
        pos = n.get("position") or {"x": 0, "y": 0}
        if isinstance(pos, str):
            pos = json.loads(pos)
        n["position"] = pos

    # condition 欄位可能是 JSONB
    for e in edges:
        cond = e.get("condition")
        if isinstance(cond, str):
            try:
                e["condition"] = json.loads(cond)
            except Exception:
                pass

    return ApiResponse(data={"nodes": nodes, "edges": edges})


# ── 儲存工作流程 ────────────────────────────────────────────────────────────


@router.post(
    "/{app_id}/workflow",
    response_model=ApiResponse,
    summary="儲存工作流程（覆寫）",
)
async def save_workflow(
    app_id: uuid.UUID,
    body: WorkflowSave,
    session: AsyncSession = Depends(get_session),
):
    # 確認 application 存在
    check = await session.execute(
        text("SELECT id FROM applications WHERE id = :id AND status != 'deleted'"),
        {"id": str(app_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="應用程式不存在")

    # 清除舊的工作流程
    await session.execute(
        text("DELETE FROM workflow_edges WHERE application_id = :app_id"),
        {"app_id": str(app_id)},
    )
    await session.execute(
        text("DELETE FROM workflow_nodes WHERE application_id = :app_id"),
        {"app_id": str(app_id)},
    )

    # 插入節點
    for node in body.nodes:
        node_id = node.get("id") or str(uuid.uuid4())
        node_key = node.get("node_key") or node_id
        position = node.get("position") or {"x": 0, "y": 0}
        if isinstance(position, str):
            position = json.loads(position)
        await session.execute(
            text("""
                INSERT INTO workflow_nodes (id, application_id, node_type, node_key, label, config, position)
                VALUES (:id, :app_id, :node_type, :node_key, :label, :config::jsonb, :position::jsonb)
            """),
            {
                "id": node_id,
                "app_id": str(app_id),
                "node_type": node.get("node_type", "start"),
                "node_key": node_key,
                "label": node.get("label", ""),
                "config": json.dumps(node.get("config", {}), ensure_ascii=False),
                "position": json.dumps(position, ensure_ascii=False),
            },
        )

    # 插入邊
    for edge in body.edges:
        edge_id = edge.get("id") or str(uuid.uuid4())
        condition = edge.get("condition")
        condition_json = json.dumps(condition, ensure_ascii=False) if condition is not None else None
        await session.execute(
            text("""
                INSERT INTO workflow_edges (id, application_id, source_node_key, target_node_key, condition)
                VALUES (:id, :app_id, :source, :target, :condition::jsonb)
            """),
            {
                "id": edge_id,
                "app_id": str(app_id),
                "source": edge["source_node_key"],
                "target": edge["target_node_key"],
                "condition": condition_json,
            },
        )

    return ApiResponse(message="工作流程已儲存")


# ── 執行工作流程（SSE） ─────────────────────────────────────────────────────


@router.post(
    "/{app_id}/workflow/chat",
    summary="執行工作流程（SSE 串流）",
)
async def run_workflow(
    app_id: uuid.UUID,
    body: WorkflowChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # 載入節點與邊
    nodes_rows = await session.execute(
        text(
            "SELECT * FROM workflow_nodes WHERE application_id = :app_id ORDER BY created_at"
        ),
        {"app_id": str(app_id)},
    )
    edges_rows = await session.execute(
        text("SELECT * FROM workflow_edges WHERE application_id = :app_id"),
        {"app_id": str(app_id)},
    )
    nodes = [dict(r._mapping) for r in nodes_rows.fetchall()]
    edges = [dict(r._mapping) for r in edges_rows.fetchall()]

    if not nodes:
        raise HTTPException(status_code=400, detail="工作流程尚未設定，請先建立節點")

    for n in nodes:
        if isinstance(n.get("config"), str):
            n["config"] = json.loads(n["config"])

    executor = WorkflowExecutor(nodes=nodes, edges=edges)

    async def event_generator():
        async for event in executor.execute(
            user_input=body.user_input,
            user_id=request.headers.get("X-User-ID", "anonymous"),
        ):
            yield event

    return EventSourceResponse(event_generator())
