"""Natural-language → workflow JSON generator — v4.9 I.

Pipeline:
1. User prompt (e.g. "我要做請假審批 workflow")
2. Build LLM prompt with available node types schema + few-shot examples
3. Call LLM (use workspace's default provider/model)
4. Parse JSON response, validate against schema
5. Return as workflow draft (front-end import 進 LogicFlow editor)
"""
from __future__ import annotations
import json
import re
from typing import Any

import structlog

log = structlog.get_logger()


# Available nodes catalog（簡化版 — 給 LLM 看的）
AVAILABLE_NODES = [
    {"type": "start", "desc": "entry point, no config"},
    {"type": "llm", "desc": "LLM chat. config: { model, system_prompt, prompt_template }"},
    {"type": "knowledge_retrieval", "desc": "RAG retrieve. config: { kb_ids: [], top_k, search_mode: hybrid|vector|fts }"},
    {"type": "answer", "desc": "stream final answer. config: { message_template, stream: true }"},
    {"type": "condition", "desc": "branch if. config: { conditions: [{variable, operator, value}], logic: AND|OR }"},
    {"type": "loop", "desc": "iterate. config: { loop_type: list, list_variable, item_variable, max_iterations }"},
    {"type": "http_request", "desc": "HTTP call. config: { method, url, headers, body_template, output_variable, timeout }"},
    {"type": "human_approval", "desc": "pause for admin approval. config: { approver_role, payload_template }"},
    {"type": "sub_workflow", "desc": "call another workflow. config: { sub_application_id, input_template, output_variable }"},
    {"type": "form", "desc": "collect user input. config: { fields: [{name, label, type, required}] }"},
    {"type": "email", "desc": "send email. config: { to_var, subject_template, body_template }"},
    {"type": "webhook", "desc": "receive external trigger. config: { path, secret, output_variable }"},
    {"type": "transform", "desc": "transform data. config: { input_variable, expression, output_variable }"},
    {"type": "mcp_tool", "desc": "MCP tool call. config: { server_url, tool_name, tool_params_template, output_variable }"},
    {"type": "code", "desc": "run sandboxed Python `def run(**kwargs)->dict`. config: { code, inputs:[{name,value_expression}], output_variable }"},
]


SYSTEM_PROMPT = """你是 staffKM workflow 設計專家。根據使用者需求，產出可直接 import 的 workflow JSON。

可用的 node types:
{node_catalog}

規則:
1. 必須有一個 start node
2. nodes 用 unique node_key（snake_case）
3. edges 連接 source_node_key → target_node_key
4. 大部分流程需要：start → [retrieval/condition/loop] → llm → answer
5. config 結構要符合對應 node type
6. 只輸出 JSON，不要解釋

範例輸出 (請假審批):
```json
{{
  "name": "leave_approval",
  "description": "請假申請審批流程",
  "nodes": [
    {{"node_key": "start", "node_type": "start", "config": {{}}}},
    {{"node_key": "collect", "node_type": "form", "config": {{"fields": [{{"name": "days", "label": "請假天數", "type": "number", "required": true}}]}}}},
    {{"node_key": "check_policy", "node_type": "condition", "config": {{"conditions": [{{"variable": "days", "operator": ">", "value": 3}}], "logic": "AND"}}}},
    {{"node_key": "approval", "node_type": "human_approval", "config": {{"approver_role": "manager", "payload_template": "{{collect_form_data}}"}}}},
    {{"node_key": "notify", "node_type": "email", "config": {{"to_var": "user_email", "subject_template": "請假已核准", "body_template": "您的請假 {{days}} 天已核准"}}}}
  ],
  "edges": [
    {{"source_node_key": "start", "target_node_key": "collect"}},
    {{"source_node_key": "collect", "target_node_key": "check_policy"}},
    {{"source_node_key": "check_policy", "target_node_key": "approval"}},
    {{"source_node_key": "approval", "target_node_key": "notify"}}
  ]
}}
```

現在請根據使用者需求產出 workflow JSON："""


def _build_prompt(user_request: str) -> str:
    catalog = "\n".join(f"- `{n['type']}`: {n['desc']}" for n in AVAILABLE_NODES)
    return SYSTEM_PROMPT.format(node_catalog=catalog) + f"\n\n使用者需求: {user_request}\n\n輸出："


def _extract_json(text: str) -> dict:
    """從 LLM response 抓 JSON block（容錯 markdown code fence）。"""
    # 試 ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # 試直接是 JSON object
    m2 = re.search(r"(\{[\s\S]*\})", text)
    if m2:
        return json.loads(m2.group(1))
    raise ValueError("no JSON in LLM response")


def _validate(workflow: dict) -> tuple[bool, list[str]]:
    """簡單 schema 檢查；回 (ok, errors)。"""
    errors: list[str] = []
    if "nodes" not in workflow or not isinstance(workflow["nodes"], list):
        errors.append("missing nodes")
    if "edges" not in workflow or not isinstance(workflow["edges"], list):
        errors.append("missing edges")
    if errors:
        return False, errors

    valid_types = {n["type"] for n in AVAILABLE_NODES}
    node_keys: set[str] = set()
    for n in workflow["nodes"]:
        if "node_key" not in n or "node_type" not in n:
            errors.append(f"node missing node_key/node_type: {n}")
            continue
        if n["node_type"] not in valid_types:
            errors.append(f"unknown node_type: {n['node_type']}")
        if n["node_key"] in node_keys:
            errors.append(f"duplicate node_key: {n['node_key']}")
        node_keys.add(n["node_key"])

    has_start = any(n.get("node_type") == "start" for n in workflow["nodes"])
    if not has_start:
        errors.append("no start node")

    for e in workflow["edges"]:
        if "source_node_key" not in e or "target_node_key" not in e:
            errors.append(f"edge missing keys: {e}")
            continue
        if e["source_node_key"] not in node_keys:
            errors.append(f"edge source not in nodes: {e['source_node_key']}")
        if e["target_node_key"] not in node_keys:
            errors.append(f"edge target not in nodes: {e['target_node_key']}")

    return len(errors) == 0, errors


async def generate_workflow(
    user_request: str,
    *,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """Call LLM and return validated workflow dict.

    Returns:
        {"workflow": {...}, "valid": bool, "errors": [...], "raw_response": "..."}
    """
    import httpx

    prompt = _build_prompt(user_request)

    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 2000,
                },
            )
            r.raise_for_status()
            response_text = r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.error("workflow_gen_llm_failed", error=str(e))
        return {"workflow": None, "valid": False, "errors": [f"LLM call failed: {e}"], "raw_response": ""}

    try:
        workflow = _extract_json(response_text)
    except Exception as e:
        return {"workflow": None, "valid": False, "errors": [f"JSON parse failed: {e}"], "raw_response": response_text}

    valid, errors = _validate(workflow)
    log.info("workflow_gen_done", valid=valid, errors_count=len(errors),
             nodes=len(workflow.get("nodes", [])), edges=len(workflow.get("edges", [])))
    return {"workflow": workflow, "valid": valid, "errors": errors, "raw_response": response_text}
