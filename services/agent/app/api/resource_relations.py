"""Resource Relations API — 對齊 MaxKB v2.9「關聯資源」(Associated Resources)。

提供 2 個端點，回傳指定資源的雙向依賴：
  GET /resources/{resource_type}/{resource_id}/depends-on  — 它依賴了誰
  GET /resources/{resource_type}/{resource_id}/used-by     — 它被誰依賴

支援 resource_type：
  application | knowledge_base | tool | skill | model | mcp_server | workflow

回傳格式（ApiResponse.data 為 list of relations）：
  [{ resource_type, id, name, url }]

實作策略：
  - application 表層欄位 (knowledge_base_ids / skill_ids / llm_model_id)：直接 SQL
  - workflow node config 內引用 (kb_id / kb_ids / sub_application_id / server_url)：
    JSONB path query；對 model / tool name 等 string ref 用 LIKE 比對節點 config
  - workspace 過濾：透過 TenantContext，所有查詢都 AND workspace_id

注意：
  - KB.embedding_model 是 string（非 FK）→ 不視為 model dependency
  - workflow node 內的 model 多半也是 model_name 字串而非 ai_models.id
    → KB / model 反查走 model_name 字串相符（best-effort）
  - mcp_server 反查走 server_url 字串相符
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member


router = APIRouter()


RESOURCE_TYPES = {
    "application", "knowledge_base", "tool", "skill",
    "model", "mcp_server", "workflow",
}


def _url_for(resource_type: str, rid: str) -> str:
    mapping = {
        "application":     f"/applications/{rid}",
        "knowledge_base":  f"/knowledge/{rid}",
        "tool":            f"/tools/{rid}",
        "skill":           f"/skills/{rid}",
        "model":           f"/admin/models/{rid}",
        "mcp_server":      f"/mcp/{rid}",
        "workflow":        f"/applications/{rid}/workflow",
    }
    return mapping.get(resource_type, "")


def _mk(rtype: str, rid: Any, name: Any) -> dict[str, Any]:
    rid_s = str(rid) if rid is not None else ""
    return {
        "resource_type": rtype,
        "id":            rid_s,
        "name":          name or "",
        "url":           _url_for(rtype, rid_s),
    }


async def _fetch_resource_meta(
    session: AsyncSession, ws: str, rtype: str, rid: str
) -> dict[str, Any] | None:
    """確認 resource 存在於當前 workspace，並回傳基本欄位（name 等）。"""
    table_map = {
        "application":     ("applications",      "id, name"),
        "knowledge_base":  ("knowledge_bases",   "id, name"),
        "tool":            ("tools",             "id, name"),
        "skill":           ("skills",            "id, name"),
        "mcp_server":      ("mcp_servers",       "id, name, url"),
        "workflow":        ("applications",      "id, name"),  # workflow 屬於 application
    }
    if rtype == "model":
        # ai_models 為 cluster-wide registry，無 workspace_id
        row = await session.execute(
            text("SELECT id, model_name AS name FROM ai_models WHERE id = CAST(:rid AS uuid)"),
            {"rid": rid},
        )
        r = row.fetchone()
        return dict(r._mapping) if r else None

    if rtype not in table_map:
        return None
    table, cols = table_map[rtype]
    row = await session.execute(
        text(f"SELECT {cols} FROM {table} WHERE id = CAST(:rid AS uuid) AND workspace_id = CAST(:ws AS uuid)"),  # noqa: S608
        {"rid": rid, "ws": ws},
    )
    r = row.fetchone()
    return dict(r._mapping) if r else None


async def _collect_app_deps(
    session: AsyncSession, ws: str, app_id: str
) -> list[dict[str, Any]]:
    """收集 application 直接依賴的 KB / Skill / Model + workflow node 引用的資源。"""
    deps: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _add(rtype: str, rid: Any, name: Any) -> None:
        rid_s = str(rid) if rid is not None else ""
        key = (rtype, rid_s)
        if not rid_s or key in seen:
            return
        seen.add(key)
        deps.append(_mk(rtype, rid_s, name))

    # 1. application 表層欄位
    row = await session.execute(
        text("""
            SELECT knowledge_base_ids, skill_ids, llm_model_id, config
            FROM applications
            WHERE id = CAST(:rid AS uuid) AND workspace_id = CAST(:ws AS uuid)
        """),
        {"rid": app_id, "ws": ws},
    )
    app_row = row.fetchone()
    if not app_row:
        return deps

    kb_ids = app_row._mapping["knowledge_base_ids"] or []
    skill_ids = app_row._mapping["skill_ids"] or []
    llm_model_id = app_row._mapping["llm_model_id"]
    app_config = app_row._mapping["config"] or {}

    # 防呆：JSONB 欄位可能是 str
    if isinstance(kb_ids, str):
        try:    kb_ids = json.loads(kb_ids)
        except Exception:    kb_ids = []
    if isinstance(skill_ids, str):
        try:    skill_ids = json.loads(skill_ids)
        except Exception:    skill_ids = []
    if isinstance(app_config, str):
        try:    app_config = json.loads(app_config)
        except Exception:    app_config = {}

    # KB
    if kb_ids:
        kb_rows = await session.execute(
            text("""
                SELECT id, name FROM knowledge_bases
                WHERE id::text = ANY(:ids) AND workspace_id = CAST(:ws AS uuid)
            """),
            {"ids": [str(x) for x in kb_ids], "ws": ws},
        )
        for r in kb_rows.fetchall():
            _add("knowledge_base", r._mapping["id"], r._mapping["name"])

    # Skill
    if skill_ids:
        skill_rows = await session.execute(
            text("""
                SELECT id, name FROM skills
                WHERE id::text = ANY(:ids) AND workspace_id = CAST(:ws AS uuid)
            """),
            {"ids": [str(x) for x in skill_ids], "ws": ws},
        )
        for r in skill_rows.fetchall():
            _add("skill", r._mapping["id"], r._mapping["name"])

    # LLM model
    if llm_model_id:
        m_row = await session.execute(
            text("SELECT id, model_name FROM ai_models WHERE id = CAST(:rid AS uuid)"),
            {"rid": str(llm_model_id)},
        )
        m = m_row.fetchone()
        if m:
            _add("model", m._mapping["id"], m._mapping["model_name"])

    # reranker model（在 config.reranker_model_id）
    reranker_id = None
    if isinstance(app_config, dict):
        reranker_id = app_config.get("reranker_model_id")
    if reranker_id:
        m_row = await session.execute(
            text("SELECT id, model_name FROM ai_models WHERE id = CAST(:rid AS uuid)"),
            {"rid": str(reranker_id)},
        )
        m = m_row.fetchone()
        if m:
            _add("model", m._mapping["id"], m._mapping["model_name"])

    # 2. workflow_nodes 內引用
    nodes_rows = await session.execute(
        text("""
            SELECT node_type, config FROM workflow_nodes
            WHERE application_id = CAST(:rid AS uuid) AND workspace_id = CAST(:ws AS uuid)
        """),
        {"rid": app_id, "ws": ws},
    )
    nodes = nodes_rows.fetchall()

    # 收集 string refs（之後一次反查）
    sub_app_ids: set[str] = set()
    kb_id_refs: set[str] = set()
    model_name_refs: set[str] = set()
    mcp_server_urls: set[str] = set()
    tool_name_refs: set[str] = set()

    for n in nodes:
        cfg = n._mapping["config"]
        if isinstance(cfg, str):
            try:    cfg = json.loads(cfg)
            except Exception:    cfg = {}
        if not isinstance(cfg, dict):
            continue
        # sub_workflow → application_id
        sub_app = cfg.get("sub_application_id")
        if sub_app:
            sub_app_ids.add(str(sub_app))
        # knowledge_retrieval / kb_writer → kb_id / kb_ids
        kb_id = cfg.get("kb_id")
        if kb_id:
            kb_id_refs.add(str(kb_id))
        for k in (cfg.get("kb_ids") or []):
            if k:
                kb_id_refs.add(str(k))
        # llm / image_understand 等 → model（字串 model_name）
        mname = cfg.get("model")
        if mname and isinstance(mname, str):
            model_name_refs.add(mname)
        # mcp_tool → server_url
        surl = cfg.get("server_url")
        if surl and isinstance(surl, str):
            mcp_server_urls.add(surl.rstrip("/"))
        # tool_name（mcp_tool 內也有）
        tname = cfg.get("tool_name")
        if tname and isinstance(tname, str):
            tool_name_refs.add(tname)

    # sub application
    if sub_app_ids:
        rows = await session.execute(
            text("""
                SELECT id, name FROM applications
                WHERE id::text = ANY(:ids) AND workspace_id = CAST(:ws AS uuid)
            """),
            {"ids": list(sub_app_ids), "ws": ws},
        )
        for r in rows.fetchall():
            _add("application", r._mapping["id"], r._mapping["name"])

    # KB refs from nodes
    if kb_id_refs:
        rows = await session.execute(
            text("""
                SELECT id, name FROM knowledge_bases
                WHERE id::text = ANY(:ids) AND workspace_id = CAST(:ws AS uuid)
            """),
            {"ids": list(kb_id_refs), "ws": ws},
        )
        for r in rows.fetchall():
            _add("knowledge_base", r._mapping["id"], r._mapping["name"])

    # model refs by model_name（ai_models 為全域，不過 workspace 過濾）
    if model_name_refs:
        rows = await session.execute(
            text("SELECT id, model_name FROM ai_models WHERE model_name = ANY(:names)"),
            {"names": list(model_name_refs)},
        )
        for r in rows.fetchall():
            _add("model", r._mapping["id"], r._mapping["model_name"])

    # mcp server by url
    if mcp_server_urls:
        rows = await session.execute(
            text("""
                SELECT id, name, url FROM mcp_servers
                WHERE rtrim(url, '/') = ANY(:urls) AND workspace_id = CAST(:ws AS uuid)
            """),
            {"urls": list(mcp_server_urls), "ws": ws},
        )
        for r in rows.fetchall():
            _add("mcp_server", r._mapping["id"], r._mapping["name"])

    # tool by name（best-effort，因為 mcp_tool 的 tool_name 是 MCP tool 字串）
    if tool_name_refs:
        rows = await session.execute(
            text("""
                SELECT id, name FROM tools
                WHERE name = ANY(:names) AND workspace_id = CAST(:ws AS uuid)
            """),
            {"names": list(tool_name_refs), "ws": ws},
        )
        for r in rows.fetchall():
            _add("tool", r._mapping["id"], r._mapping["name"])

    return deps


async def _find_apps_using(
    session: AsyncSession, ws: str, ref_type: str, ref_id: str, ref_name: str | None = None,
) -> list[dict[str, Any]]:
    """反查哪些 application 用到此資源（含 workflow node 內的引用）。"""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(app_id: Any, name: Any) -> None:
        aid = str(app_id)
        if aid in seen:
            return
        seen.add(aid)
        found.append(_mk("application", aid, name))

    rid_str = str(ref_id)

    # 1. application 表層
    if ref_type == "knowledge_base":
        rows = await session.execute(
            text("""
                SELECT id, name FROM applications
                WHERE workspace_id = CAST(:ws AS uuid)
                  AND status != 'deleted'
                  AND knowledge_base_ids @> CAST(:val AS jsonb)
            """),
            {"ws": ws, "val": json.dumps([rid_str])},
        )
        for r in rows.fetchall():
            _add(r._mapping["id"], r._mapping["name"])
    elif ref_type == "skill":
        rows = await session.execute(
            text("""
                SELECT id, name FROM applications
                WHERE workspace_id = CAST(:ws AS uuid)
                  AND status != 'deleted'
                  AND skill_ids @> CAST(:val AS jsonb)
            """),
            {"ws": ws, "val": json.dumps([rid_str])},
        )
        for r in rows.fetchall():
            _add(r._mapping["id"], r._mapping["name"])
    elif ref_type == "model":
        rows = await session.execute(
            text("""
                SELECT id, name FROM applications
                WHERE workspace_id = CAST(:ws AS uuid)
                  AND status != 'deleted'
                  AND (llm_model_id = CAST(:rid AS uuid)
                       OR config @> CAST(:rerank AS jsonb))
            """),
            {"ws": ws, "rid": rid_str, "rerank": json.dumps({"reranker_model_id": rid_str})},
        )
        for r in rows.fetchall():
            _add(r._mapping["id"], r._mapping["name"])

    # 2. workflow_nodes 反查（JSONB containment）
    if ref_type == "knowledge_base":
        # 對 kb_id 或 kb_ids array
        rows = await session.execute(
            text("""
                SELECT DISTINCT a.id, a.name
                FROM workflow_nodes wn
                JOIN applications a ON a.id = wn.application_id
                WHERE wn.workspace_id = CAST(:ws AS uuid)
                  AND a.status != 'deleted'
                  AND (wn.config @> CAST(:kb_id AS jsonb)
                       OR wn.config @> CAST(:kb_ids AS jsonb))
            """),
            {
                "ws": ws,
                "kb_id":  json.dumps({"kb_id": rid_str}),
                "kb_ids": json.dumps({"kb_ids": [rid_str]}),
            },
        )
        for r in rows.fetchall():
            _add(r._mapping["id"], r._mapping["name"])
    elif ref_type == "application":
        # sub_workflow node 指到此 application
        rows = await session.execute(
            text("""
                SELECT DISTINCT a.id, a.name
                FROM workflow_nodes wn
                JOIN applications a ON a.id = wn.application_id
                WHERE wn.workspace_id = CAST(:ws AS uuid)
                  AND a.status != 'deleted'
                  AND a.id != CAST(:rid AS uuid)
                  AND wn.config @> CAST(:val AS jsonb)
            """),
            {"ws": ws, "rid": rid_str, "val": json.dumps({"sub_application_id": rid_str})},
        )
        for r in rows.fetchall():
            _add(r._mapping["id"], r._mapping["name"])
    elif ref_type == "model" and ref_name:
        rows = await session.execute(
            text("""
                SELECT DISTINCT a.id, a.name
                FROM workflow_nodes wn
                JOIN applications a ON a.id = wn.application_id
                WHERE wn.workspace_id = CAST(:ws AS uuid)
                  AND a.status != 'deleted'
                  AND wn.config @> CAST(:val AS jsonb)
            """),
            {"ws": ws, "val": json.dumps({"model": ref_name})},
        )
        for r in rows.fetchall():
            _add(r._mapping["id"], r._mapping["name"])
    elif ref_type == "mcp_server":
        # 取 mcp_server.url，反查 workflow_nodes.config.server_url
        srv_row = await session.execute(
            text("SELECT url FROM mcp_servers WHERE id = CAST(:rid AS uuid) AND workspace_id = CAST(:ws AS uuid)"),
            {"rid": rid_str, "ws": ws},
        )
        srv = srv_row.fetchone()
        if srv and srv._mapping["url"]:
            srv_url = srv._mapping["url"].rstrip("/")
            rows = await session.execute(
                text("""
                    SELECT DISTINCT a.id, a.name
                    FROM workflow_nodes wn
                    JOIN applications a ON a.id = wn.application_id
                    WHERE wn.workspace_id = CAST(:ws AS uuid)
                      AND a.status != 'deleted'
                      AND (wn.config @> CAST(:v1 AS jsonb) OR wn.config @> CAST(:v2 AS jsonb))
                """),
                {
                    "ws": ws,
                    "v1": json.dumps({"server_url": srv_url}),
                    "v2": json.dumps({"server_url": srv_url + "/"}),
                },
            )
            for r in rows.fetchall():
                _add(r._mapping["id"], r._mapping["name"])
    elif ref_type == "tool" and ref_name:
        rows = await session.execute(
            text("""
                SELECT DISTINCT a.id, a.name
                FROM workflow_nodes wn
                JOIN applications a ON a.id = wn.application_id
                WHERE wn.workspace_id = CAST(:ws AS uuid)
                  AND a.status != 'deleted'
                  AND wn.config @> CAST(:val AS jsonb)
            """),
            {"ws": ws, "val": json.dumps({"tool_name": ref_name})},
        )
        for r in rows.fetchall():
            _add(r._mapping["id"], r._mapping["name"])

    return found


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get(
    "/{resource_type}/{resource_id}/depends-on",
    response_model=ApiResponse,
    summary="列出此資源所依賴的其他資源（它用了誰）",
)
async def list_dependencies(
    resource_type: str,
    resource_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    if resource_type not in RESOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支援的資源類型：{resource_type}")

    ws = str(ctx.workspace_id)
    rid = str(resource_id)

    meta = await _fetch_resource_meta(session, ws, resource_type, rid)
    if not meta:
        raise HTTPException(status_code=404, detail="找不到資源或不屬於此工作區")

    if resource_type in ("application", "workflow"):
        deps = await _collect_app_deps(session, ws, rid)
    else:
        # 其他 leaf 資源目前沒有對外依賴（KB.embedding_model 是 string、非 FK，故略）
        deps = []

    return ApiResponse(data=deps)


@router.get(
    "/{resource_type}/{resource_id}/used-by",
    response_model=ApiResponse,
    summary="列出哪些資源使用了此資源（誰用了我）",
)
async def list_dependents(
    resource_type: str,
    resource_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    if resource_type not in RESOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支援的資源類型：{resource_type}")

    ws = str(ctx.workspace_id)
    rid = str(resource_id)

    meta = await _fetch_resource_meta(session, ws, resource_type, rid)
    if not meta:
        raise HTTPException(status_code=404, detail="找不到資源或不屬於此工作區")

    name = meta.get("name") if isinstance(meta, dict) else None
    used_by = await _find_apps_using(session, ws, resource_type, rid, ref_name=name)
    return ApiResponse(data=used_by)
