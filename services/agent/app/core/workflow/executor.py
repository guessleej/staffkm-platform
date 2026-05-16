"""Workflow Executor — 依 DAG 順序執行節點"""
import base64
import json
import re
import httpx
import structlog
from typing import AsyncIterator, Any
from openai import AsyncOpenAI
from app.config import settings

log = structlog.get_logger()


_VALID_MANAGERS = ("simple", "parallel", "retry", "batch", "sandbox")


class WorkflowExecutor:
    def __init__(
        self,
        nodes: list[dict],
        edges: list[dict],
        app_config: dict = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        roles: list[str] | None = None,
        workflow_manager: str = "simple",  # M2-2: simple/parallel/retry/batch/sandbox
    ):
        # M2-2：執行策略
        if workflow_manager not in _VALID_MANAGERS:
            log.warning("workflow_manager_unknown", got=workflow_manager, fallback="simple")
            workflow_manager = "simple"
        self.workflow_manager = workflow_manager
        # 以 node_key 作為索引
        self.nodes = {n["node_key"]: n for n in nodes}
        self.edges = edges
        self.app_config = app_config or {}
        # RFC-001 Stage 2：多租戶上下文，於 _exec_* 呼叫下游服務時帶入
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.roles = roles or []
        # 建立有向圖（key -> [key, ...]）
        self.children: dict[str, list[str]] = {n: [] for n in self.nodes}
        self.edge_conditions: dict[tuple, Any] = {}
        for edge in edges:
            src, tgt = edge["source_node_key"], edge["target_node_key"]
            if src in self.children:
                self.children[src].append(tgt)
            self.edge_conditions[(src, tgt)] = edge.get("condition")

    def _find_start_node(self) -> str | None:
        targets = {e["target_node_key"] for e in self.edges}
        # 先找 type == start 的節點
        for key, node in self.nodes.items():
            if node.get("node_type") == "start":
                return key
        # fallback：找沒有被任何邊指向的節點
        for key in self.nodes:
            if key not in targets:
                return key
        return next(iter(self.nodes)) if self.nodes else None

    async def execute(
        self, user_input: str, user_id: str = "anonymous"
    ) -> AsyncIterator[dict]:
        """執行工作流程，以 SSE 事件方式 yield 結果"""
        # 多租戶上下文塞進 context dict，所有 _exec_* node 都能讀到
        context: dict[str, Any] = {
            "user_input": user_input,
            "workspace_id": self.workspace_id,
            "_user_id": user_id or self.user_id,
            "_roles": self.roles,
        }
        current_key = self._find_start_node()
        visited = set()
        # M2-2：每個 node 的累計嘗試次數（retry manager 用）
        _node_attempts: dict[str, int] = {}

        # 啟動 log 帶 manager 策略
        log.info(
            "workflow_execute_start",
            manager=self.workflow_manager,
            workspace_id=str(self.workspace_id or "-"),
            user_id=str(self.user_id or "-"),
            node_count=len(self.nodes),
        )

        # M2-2 → M2 收尾-A：parallel 與 batch 已有真實語義；sandbox 仍為 stub
        if self.workflow_manager == "sandbox":
            log.warning(
                "workflow_manager_stub",
                manager="sandbox",
                note="sandbox 容器隔離尚未實作（M4），本次以 simple 模式執行",
            )

        while current_key and current_key not in visited:
            visited.add(current_key)
            node = self.nodes.get(current_key)
            if not node:
                break

            node_type = node.get("node_type", "")
            config = node.get("config", {})
            if isinstance(config, str):
                config = json.loads(config)

            yield {"event": "node_start", "data": json.dumps({"node_key": current_key, "type": node_type})}

            next_key = None
            try:
                if node_type == "start":
                    pass  # start 節點只設定初始 context

                elif node_type == "knowledge_retrieval":
                    results = await self._exec_knowledge(config, context)
                    context["knowledge_results"] = results

                elif node_type == "llm":
                    async for token in self._exec_llm(config, context):
                        yield {"event": "token", "data": token}
                    # llm_response 在 _exec_llm 裡設定

                elif node_type == "condition":
                    branch = self._eval_condition(config, context)
                    raw = config.get("true_branch") if branch else config.get("false_branch")
                    next_key = self._resolve_next_node_key(raw)

                elif node_type == "variable":
                    for assignment in config.get("assignments", []):
                        name = assignment.get("name")
                        expr = assignment.get("value_expression", "")
                        if name:
                            context[name] = self._render_template(expr, context)

                elif node_type == "http_request":
                    result = await self._exec_http(config, context)
                    context["http_response"] = result

                elif node_type == "answer":
                    content = self._render_template(
                        config.get("content_template", "{{llm_response}}"), context
                    )
                    for char in content:
                        yield {"event": "token", "data": char}

                elif node_type == "loop":
                    async for ev in self._exec_loop(config, context):
                        yield ev

                elif node_type == "intent":
                    label, resolved_key = await self._exec_intent(config, context)
                    context["intent"] = label
                    if resolved_key:
                        next_key = resolved_key

                elif node_type == "parameter_extraction":
                    await self._exec_parameter_extraction(config, context)

                elif node_type == "reranker":
                    await self._exec_reranker(config, context)

                elif node_type == "speech_to_text":
                    await self._exec_stt(config, context)

                elif node_type == "text_to_speech":
                    await self._exec_tts(config, context)

                elif node_type == "image_understand":
                    async for token in self._exec_image_understand(config, context):
                        yield {"event": "token", "data": token}

                elif node_type == "image_generate":
                    await self._exec_image_generate(config, context)

                elif node_type == "document_extract":
                    await self._exec_document_extract(config, context)

                elif node_type == "document_split":
                    await self._exec_document_split(config, context)

                elif node_type == "form":
                    async for ev in self._exec_form(config, context):
                        yield ev

                elif node_type == "mcp_tool":
                    await self._exec_mcp_tool(config, context)

                # ── M2-1 新節點 ────────────────────────────────────
                elif node_type == "wait":
                    await self._exec_wait(config, context)
                elif node_type == "switch":
                    next_key = await self._exec_switch(config, context)
                elif node_type == "map":
                    async for ev in self._exec_map(config, context):
                        yield ev
                elif node_type == "reduce":
                    await self._exec_reduce(config, context)
                elif node_type == "webhook":
                    await self._exec_webhook(config, context)
                elif node_type == "notify":
                    await self._exec_notify(config, context)
                elif node_type == "email":
                    await self._exec_email(config, context)
                elif node_type == "schedule":
                    await self._exec_schedule(config, context)
                elif node_type == "transform":
                    await self._exec_transform(config, context)
                elif node_type == "merge":
                    await self._exec_merge(config, context)

            except Exception as e:
                # M2-2：manager='retry' 時自動重試（最多 3 次、指數退避）
                attempts = _node_attempts.get(current_key, 0) + 1
                _node_attempts[current_key] = attempts
                max_attempts = 3 if self.workflow_manager == "retry" else 1
                if attempts < max_attempts:
                    import asyncio
                    backoff_ms = 500 * (2 ** (attempts - 1))
                    log.warning(
                        "workflow_node_retry",
                        node_key=current_key, type=node_type, attempt=attempts,
                        backoff_ms=backoff_ms, error=str(e),
                        **self._audit_fields(context),
                    )
                    yield {"event": "retry", "data": json.dumps({
                        "node_key": current_key, "attempt": attempts, "backoff_ms": backoff_ms,
                    })}
                    await asyncio.sleep(backoff_ms / 1000.0)
                    visited.discard(current_key)   # 取消 visited 標記讓 while 重跑該節點
                    continue
                # 超出 retry 上限或非 retry 策略
                log.error(
                    "workflow_node_failed",
                    node_key=current_key, type=node_type, error=str(e),
                    attempts=attempts, manager=self.workflow_manager,
                    **self._audit_fields(context),
                )
                yield {"event": "error", "data": json.dumps({"node_key": current_key, "error": str(e)})}

            yield {"event": "node_done", "data": json.dumps({"node_key": current_key})}

            # 選擇下一個節點（condition 已設定 next_key）
            if next_key is None:
                children = self.children.get(current_key, [])
                # 排除 condition 分支（condition 已由節點本身處理）
                non_condition = [
                    c for c in children
                    if self.edge_conditions.get((current_key, c)) is None
                ]
                # M2 收尾-A：parallel manager — 多子節點時並行展開
                if self.workflow_manager == "parallel" and len(non_condition) >= 2:
                    async for ev in self._execute_parallel_branches(non_condition, context, visited):
                        yield ev
                    next_key = None
                else:
                    next_key = non_condition[0] if non_condition else None

            current_key = next_key

        yield {"event": "citations", "data": json.dumps(context.get("knowledge_results", []))}
        yield {"event": "done", "data": "[DONE]"}

    # ── M2 收尾-A：parallel manager 真實語義 ────────────────────────────
    async def _execute_subchain(
        self, start_key: str, ctx_snapshot: dict
    ) -> tuple[list[dict], dict]:
        """走完從 start_key 開始的子鏈，回 (events, ctx_after)。供 parallel branch 用。

        簡化規則：
        - 子鏈內遇到 fan-out 不再展開（避免遞迴爆炸；M4 再支援巢狀並行）
        - 子鏈使用 ctx_snapshot 的 shallow copy，避免污染主 context
        - 子鏈以 simple 策略執行（不繼承父 workflow_manager；避免無限遞迴）
        """
        local_ctx = dict(ctx_snapshot)
        events: list[dict] = []
        cur = start_key
        local_visited: set[str] = set()

        # 為避免重入 self.execute() 帶來的複雜性，這裡只支援常見 5 種 node type 的子鏈
        # （llm / variable / answer / http_request / knowledge_retrieval），
        # 其它 type 直接退出子鏈（事件不丟）。
        SAFE_TYPES = {"llm", "variable", "answer", "http_request", "knowledge_retrieval", "start"}

        while cur and cur not in local_visited:
            local_visited.add(cur)
            node = self.nodes.get(cur)
            if not node:
                break
            ntype = node.get("node_type", "")
            cfg = node.get("config", {})
            if isinstance(cfg, str):
                cfg = json.loads(cfg)

            events.append({"event": "parallel_node_start",
                           "data": json.dumps({"node_key": cur, "type": ntype})})

            if ntype not in SAFE_TYPES:
                events.append({"event": "parallel_skip",
                               "data": json.dumps({"node_key": cur, "type": ntype,
                                                   "reason": "non-safe type in parallel branch"})})
                break

            try:
                if ntype == "llm":
                    async for tok in self._exec_llm(cfg, local_ctx):
                        events.append({"event": "token", "data": tok})
                elif ntype == "variable":
                    for a in cfg.get("assignments", []):
                        n = a.get("name")
                        if n:
                            local_ctx[n] = self._render_template(a.get("value_expression", ""), local_ctx)
                elif ntype == "http_request":
                    local_ctx["http_response"] = await self._exec_http(cfg, local_ctx)
                elif ntype == "knowledge_retrieval":
                    local_ctx["knowledge_results"] = await self._exec_knowledge(cfg, local_ctx)
                elif ntype == "answer":
                    content = self._render_template(cfg.get("content_template", "{{llm_response}}"), local_ctx)
                    for ch in content:
                        events.append({"event": "token", "data": ch})
            except Exception as e:
                events.append({"event": "parallel_error",
                               "data": json.dumps({"node_key": cur, "error": str(e)})})

            events.append({"event": "parallel_node_done", "data": json.dumps({"node_key": cur})})

            # 子鏈內挑下一個（不再 fan-out）
            cs = self.children.get(cur, [])
            non_c = [c for c in cs if self.edge_conditions.get((cur, c)) is None]
            cur = non_c[0] if non_c else None

        return events, local_ctx

    async def _execute_parallel_branches(
        self, start_keys: list[str], context: dict, visited: set[str]
    ) -> AsyncIterator[dict]:
        """同時走多個 branch，gather 完成後把 branch context merge 回主 context。

        - 各 branch 共享父 context 快照（shallow copy）
        - 衝突欄位採「最後勝」策略；保留各 branch 的 llm_response 到
          context["__parallel_results__"][branch_idx]
        """
        import asyncio

        snapshot = {k: v for k, v in context.items()}
        yield {"event": "parallel_start",
               "data": json.dumps({"branches": start_keys, "count": len(start_keys)})}

        tasks = [self._execute_subchain(sk, snapshot) for sk in start_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        per_branch: list[Any] = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                yield {"event": "parallel_error",
                       "data": json.dumps({"branch": idx, "error": str(res)})}
                per_branch.append(None)
                continue
            evs, ctx_after = res
            for ev in evs:
                yield ev
            # branch context merge：以「最後勝」策略覆寫 context；llm_response 拆出來收集
            per_branch.append(ctx_after.get("llm_response"))
            for k, v in ctx_after.items():
                if k in self._INTERNAL_CONTEXT_KEYS:
                    continue
                context[k] = v
            # 子鏈內節點全部標 visited，避免主迴圈再走一次
            visited.update(start_keys)

        context["__parallel_results__"] = per_branch
        yield {"event": "parallel_done",
               "data": json.dumps({"branches": len(start_keys)})}

    # 內部欄位（不允許被 {{var}} 模板替換以避免洩漏給使用者輸出）
    _INTERNAL_CONTEXT_KEYS = {"_user_id", "_roles", "workspace_id"}

    def _render_template(self, template: str, context: dict) -> str:
        """簡單的 {{variable}} 替換；跳過內部欄位避免洩漏到 prompt / answer 中。"""
        result = template
        for key, value in context.items():
            if key in self._INTERNAL_CONTEXT_KEYS or key.startswith("__"):
                continue
            if isinstance(value, (str, int, float)):
                result = result.replace(f"{{{{{key}}}}}", str(value))
            elif isinstance(value, list) and key == "knowledge_results":
                docs = "\n\n".join(
                    f"[{d.get('doc_name', '')}]\n{d.get('content', '')}" for d in value
                )
                result = result.replace(f"{{{{{key}}}}}", docs)
        return result

    def _downstream_headers(self, context: dict) -> dict[str, str]:
        """組裝呼叫下游服務時要帶的認證 header（X-User-ID / X-User-Roles）。"""
        headers: dict[str, str] = {}
        uid = context.get("_user_id")
        roles = context.get("_roles") or []
        if uid:
            headers["X-User-ID"] = str(uid)
        if roles:
            headers["X-User-Roles"] = ",".join(roles)
        return headers

    def _audit_fields(self, context: dict) -> dict[str, str]:
        """組裝 structured log 用的審計欄位，便於跨 workspace 追蹤呼叫。"""
        return {
            "workspace_id": str(context.get("workspace_id") or "-"),
            "user_id":      str(context.get("_user_id") or "-"),
        }

    def _knowledge_url(self, context: dict, suffix: str) -> str:
        """組 knowledge service URL；有 workspace 走 v2，否則走 legacy（會被 bridge 重寫）。"""
        ws = context.get("workspace_id")
        base = settings.KNOWLEDGE_SERVICE_URL
        if ws:
            return f"{base}/api/v1/workspace/{ws}/knowledge/{suffix.lstrip('/')}"
        return f"{base}/api/v1/knowledge/{suffix.lstrip('/')}"

    async def _exec_knowledge(self, config: dict, context: dict) -> list[dict]:
        kb_ids = config.get("kb_ids", [])
        if not kb_ids:
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    self._knowledge_url(context, "search"),
                    json={
                        "query": context.get("user_input", ""),
                        "kb_ids": kb_ids,
                        "top_k": config.get("top_k", 5),
                        "similarity_threshold": config.get("similarity_threshold", 0.45),
                    },
                    headers=self._downstream_headers(context),
                )
                if resp.status_code == 200:
                    return resp.json().get("data", {}).get("citations", [])
                log.warning(
                    "workflow_knowledge_non_200",
                    status=resp.status_code, body=resp.text[:200],
                )
        except Exception as e:
            log.warning("workflow_knowledge_failed", error=str(e))
        return []

    def _build_llm_client(self, config: dict) -> tuple["AsyncOpenAI", str]:
        """建立 LLM client；強制使用 settings.LLM_MODEL（RFC-005 唯一支援模型）。

        即便 workflow config 寫了其他 model 也會被覆寫；同時把實際使用的
        endpoint / api_key 鎖定為系統預設，避免使用者手動把流量導出去。
        """
        # 強制鎖定 — 不接受 node 層 override
        base_url = settings.LLM_BASE_URL
        api_key  = settings.LLM_API_KEY or "dummy"
        model    = settings.LLM_MODEL

        # 偵測 workflow config 試圖覆寫，留 audit log
        node_model = config.get("model")
        if node_model and node_model != model:
            log.warning(
                "llm_model_override_blocked",
                requested=node_model, enforced=model,
                reason="RFC-005 onprem-llm-first 政策：僅允許單一系統 LLM 模型",
            )

        return AsyncOpenAI(api_key=api_key, base_url=base_url), model

    async def _exec_llm(self, config: dict, context: dict) -> AsyncIterator[str]:
        prompt = self._render_template(
            config.get("prompt_template", "{{user_input}}"), context
        )
        system = config.get("system_prompt", "你是一個助手，請根據提供資料回答問題。")

        # RFC-005 政策稽核：若 config 試圖蓋過系統鎖定的模型，留 audit log
        node_model = config.get("model")
        if node_model and node_model != settings.LLM_MODEL:
            log.warning(
                "llm_model_override_blocked",
                requested=node_model, enforced=settings.LLM_MODEL,
                **self._audit_fields(context),
            )

        llm, model = self._build_llm_client(config)
        full_response = ""
        try:
            stream = await llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
                temperature=float(config.get("temperature", settings.LLM_TEMPERATURE)),
                max_tokens=int(config.get("max_tokens", settings.LLM_MAX_TOKENS)),
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_response += delta
                    yield delta
        except Exception as e:
            log.error("workflow_llm_failed", error=str(e), **self._audit_fields(context))
            yield f"\n\n錯誤：LLM 呼叫失敗：{e}"
        context["llm_response"] = full_response

    def _eval_condition(self, config: dict, context: dict) -> bool:
        variable = config.get("variable", "")
        operator = config.get("operator", "contains")
        value = config.get("value", "")
        actual = str(context.get(variable, ""))
        if operator == "contains":
            return value in actual
        elif operator == "equals":
            return actual == value
        elif operator == "not_empty":
            return bool(actual.strip())
        elif operator == "is_empty":
            return not bool(actual.strip())
        return False

    async def _exec_document_extract(self, config: dict, context: dict) -> None:
        """從 URL 或 Base64 下載文件並提取純文字，存入 output_variable。"""
        input_var = config.get("input_variable", "document_url")
        output_var = config.get("output_variable", "document_text")
        input_type = config.get("input_type", "url")
        doc_input = str(context.get(input_var, ""))
        if not doc_input:
            context[output_var] = ""
            return

        try:
            if input_type == "url":
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    resp = await client.get(doc_input)
                    resp.raise_for_status()
                    raw_bytes = resp.content
                    content_type = resp.headers.get("content-type", "")
                    guessed_ext = doc_input.rstrip("/").split("/")[-1].split("?")[0].lower()
            else:
                raw_bytes = base64.b64decode(doc_input)
                content_type = config.get("mime_type", "application/octet-stream")
                guessed_ext = ""

            file_type = config.get("file_type", "auto")
            if file_type == "auto":
                if "pdf" in content_type or guessed_ext.endswith(".pdf"):
                    file_type = "pdf"
                elif any(x in content_type for x in ("word", "docx", "openxml")) or guessed_ext.endswith((".docx", ".doc")):
                    file_type = "docx"
                else:
                    file_type = "text"

            extraction_url = config.get("extraction_service_url", "")

            if file_type == "text":
                for enc in ("utf-8", "utf-8-sig", "latin-1"):
                    try:
                        context[output_var] = raw_bytes.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    context[output_var] = raw_bytes.decode("utf-8", errors="replace")

            elif extraction_url:
                ext = "pdf" if file_type == "pdf" else "docx"
                # 同 _exec_http：opt-in 內部認證轉發
                extra_headers = (
                    self._downstream_headers(context)
                    if config.get("forward_workspace_auth")
                    else {}
                )
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(
                        extraction_url,
                        files={"file": (f"document.{ext}", raw_bytes, "application/octet-stream")},
                        headers=extra_headers,
                    )
                    r.raise_for_status()
                    data = r.json()
                    context[output_var] = data.get("text", data.get("content", ""))
            else:
                context[output_var] = raw_bytes.decode("utf-8", errors="replace")

        except Exception as e:
            log.error("document_extract_failed", error=str(e))
            context[output_var] = ""

    async def _exec_document_split(self, config: dict, context: dict) -> None:
        """將長文字切分為 chunks，以 JSON 陣列字串存入 output_variable（可供 loop list 模式使用）。"""
        input_var = config.get("input_variable", "document_text")
        output_var = config.get("output_variable", "chunks")
        text = str(context.get(input_var, ""))
        if not text.strip():
            context[output_var] = "[]"
            return

        strategy = config.get("strategy", "fixed")
        chunk_size = max(1, int(config.get("chunk_size", 500)))
        chunk_overlap = max(0, min(int(config.get("chunk_overlap", 50)), chunk_size - 1))
        separator = config.get("separator", "\n\n")
        chunks: list[str] = []

        if strategy == "paragraph":
            sep = separator or "\n\n"
            paragraphs = [p.strip() for p in text.split(sep) if p.strip()]
            current = ""
            for para in paragraphs:
                if len(current) + len(para) + len(sep) <= chunk_size:
                    current = (current + sep + para).lstrip(sep)
                else:
                    if current:
                        chunks.append(current)
                    current = para
            if current:
                chunks.append(current)

        elif strategy == "sentence":
            sentences = re.split(r"(?<=[。！？.!?])\s*", text)
            sentences = [s.strip() for s in sentences if s.strip()]
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 <= chunk_size:
                    current = (current + " " + sent).strip()
                else:
                    if current:
                        chunks.append(current)
                    current = sent
            if current:
                chunks.append(current)

        elif strategy == "separator":
            sep = separator or "\n"
            chunks = [p.strip() for p in text.split(sep) if p.strip()]

        else:  # fixed
            step = chunk_size - chunk_overlap
            for i in range(0, len(text), step):
                piece = text[i : i + chunk_size]
                if piece.strip():
                    chunks.append(piece)

        context[output_var] = json.dumps(chunks, ensure_ascii=False)

    async def _exec_form(self, config: dict, context: dict) -> AsyncIterator[dict]:
        """表單節點：填入預設值並發送 form_request 事件，使前端可渲染表單。"""
        fields: list[dict] = config.get("fields", [])
        missing: list[str] = []

        for field in fields:
            name = field.get("name", "")
            if not name:
                continue
            if name not in context or context[name] == "":
                default = field.get("default", "")
                if default != "":
                    context[name] = str(default)
                elif field.get("required", False):
                    missing.append(name)

        yield {
            "event": "form_request",
            "data": json.dumps(
                {"fields": fields, "missing": missing, "filled": {f["name"]: context.get(f["name"], "") for f in fields if f.get("name")}},
                ensure_ascii=False,
            ),
        }

        if missing:
            raise RuntimeError(f"表單必填欄位未提供：{', '.join(missing)}")

    async def _exec_mcp_tool(self, config: dict, context: dict) -> None:
        """呼叫 MCP 工具（JSON-RPC 2.0 over HTTP Streamable Transport）。"""
        server_url = config.get("server_url", "").rstrip("/")
        tool_name = config.get("tool_name", "")
        output_var = config.get("output_variable", "mcp_result")
        timeout = float(config.get("timeout", 30.0))
        if not server_url or not tool_name:
            return

        params_str = self._render_template(config.get("tool_params_template", "{}"), context)
        try:
            tool_args = json.loads(params_str) if params_str.strip() else {}
        except json.JSONDecodeError:
            tool_args = {}

        headers: dict = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        api_key = config.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": tool_args},
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{server_url}/mcp", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            result = data.get("result", data)
            content_list: list = result.get("content", []) if isinstance(result, dict) else []
            if content_list:
                texts = [c["text"] for c in content_list if c.get("type") == "text" and "text" in c]
                context[output_var] = "\n".join(texts)
            else:
                context[output_var] = json.dumps(result, ensure_ascii=False)
        except Exception as e:
            log.error("mcp_tool_failed", tool=tool_name, error=str(e), **self._audit_fields(context))
            context[output_var] = f"MCP 呼叫失敗：{e}"

    async def _exec_image_understand(self, config: dict, context: dict) -> AsyncIterator[str]:
        """圖像理解：使用 Vision 模型分析圖片，串流 token 並將完整回應存入 context。"""
        input_var = config.get("input_variable", "image_url")
        input_type = config.get("input_type", "url")   # "url" | "base64"
        output_var = config.get("output_variable", "image_description")
        image_input = str(context.get(input_var, ""))
        if not image_input:
            return

        provider = config.get("provider", "openai")
        api_key = config.get("api_key", "") or (settings.OPENAI_API_KEY if provider == "openai" else "")
        model = config.get("model", "gpt-4o")
        system = config.get("system_prompt", "你是一個圖像分析助手。")
        prompt = self._render_template(config.get("prompt", "請詳細描述這張圖片的內容。"), context)
        max_tokens = int(config.get("max_tokens", 1024))
        temperature = float(config.get("temperature", 0.1))

        image_url = (
            image_input if input_type == "url"
            else f"data:image/jpeg;base64,{image_input}"
        )

        client_kwargs: dict = {"api_key": api_key}
        if config.get("base_url"):
            client_kwargs["base_url"] = config["base_url"].rstrip("/")

        llm = AsyncOpenAI(**client_kwargs)
        full_response = ""
        try:
            stream = await llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ]},
                ],
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_response += delta
                    yield delta
        except Exception as e:
            log.error("image_understand_failed", error=str(e), **self._audit_fields(context))
            yield f"\n\n錯誤：圖像分析失敗：{e}"
        context[output_var] = full_response

    async def _exec_image_generate(self, config: dict, context: dict) -> None:
        """圖像生成：呼叫 DALL-E 相容 API，將圖片 URL 或 Base64 存入 context。"""
        output_var = config.get("output_variable", "generated_image_url")
        output_type = config.get("output_type", "url")   # "url" | "base64"
        prompt = self._render_template(
            config.get("prompt_template", "{{user_input}}"), context
        )
        if not prompt:
            return

        provider = config.get("provider", "openai")
        api_key = config.get("api_key", "") or (settings.OPENAI_API_KEY if provider == "openai" else "")
        model = config.get("model", "dall-e-3")
        size = config.get("size", "1024x1024")
        n = max(1, min(4, int(config.get("n", 1))))
        response_format = "b64_json" if output_type == "base64" else "url"
        revised_var = config.get("revised_prompt_variable", "")

        client_kwargs: dict = {"api_key": api_key}
        if config.get("base_url"):
            client_kwargs["base_url"] = config["base_url"].rstrip("/")

        gen_kwargs: dict = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": response_format,
        }
        if model == "dall-e-3":
            gen_kwargs["quality"] = config.get("quality", "standard")
            gen_kwargs["style"] = config.get("style", "vivid")

        try:
            llm = AsyncOpenAI(**client_kwargs)
            resp = await llm.images.generate(**gen_kwargs)
            first = resp.data[0]
            context[output_var] = (first.b64_json or "") if output_type == "base64" else (first.url or "")
            if revised_var and first.revised_prompt:
                context[revised_var] = first.revised_prompt
        except Exception as e:
            log.error("image_generate_failed", error=str(e), **self._audit_fields(context))

    async def _exec_stt(self, config: dict, context: dict) -> None:
        """Speech-to-Text：呼叫 Whisper 相容 API，轉錄音訊後寫入 context。"""
        input_var = config.get("input_variable", "audio_url")
        output_var = config.get("output_variable", "transcription")
        input_type = config.get("input_type", "url")   # "url" | "base64"
        audio_input = str(context.get(input_var, ""))
        if not audio_input:
            return

        provider = config.get("provider", "openai")
        api_key = config.get("api_key", "") or (settings.OPENAI_API_KEY if provider == "openai" else "")
        base_url = (config.get("base_url", "") or "https://api.openai.com/v1").rstrip("/")
        model = config.get("model", "whisper-1")
        language = config.get("language", "")

        try:
            if input_type == "url":
                async with httpx.AsyncClient(timeout=30.0) as client:
                    ar = await client.get(audio_input)
                    ar.raise_for_status()
                    audio_bytes = ar.content
                    filename = audio_input.rstrip("/").split("/")[-1] or "audio.mp3"
            else:
                audio_bytes = base64.b64decode(audio_input)
                filename = "audio.mp3"

            headers: dict = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            form: dict = {"model": model}
            if language:
                form["language"] = language

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{base_url}/audio/transcriptions",
                    headers=headers,
                    files={"file": (filename, audio_bytes, "audio/mpeg")},
                    data=form,
                )
                resp.raise_for_status()
                context[output_var] = resp.json().get("text", "")
        except Exception as e:
            log.warning("stt_failed", error=str(e), **self._audit_fields(context))
            context[output_var] = ""

    async def _exec_tts(self, config: dict, context: dict) -> None:
        """Text-to-Speech：呼叫 OpenAI TTS 相容 API，將文字轉為 base64 音訊後寫入 context。"""
        input_var = config.get("input_variable", "llm_response")
        output_var = config.get("output_variable", "audio_base64")
        text = str(context.get(input_var, ""))
        if not text:
            return

        provider = config.get("provider", "openai")
        api_key = config.get("api_key", "") or (settings.OPENAI_API_KEY if provider == "openai" else "")
        base_url = (config.get("base_url", "") or "https://api.openai.com/v1").rstrip("/")
        model = config.get("model", "tts-1")
        voice = config.get("voice", "alloy")
        speed = max(0.25, min(4.0, float(config.get("speed", 1.0))))
        output_format = config.get("output_format", "mp3")

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{base_url}/audio/speech",
                    headers=headers,
                    json={
                        "model": model,
                        "input": text,
                        "voice": voice,
                        "speed": speed,
                        "response_format": output_format,
                    },
                )
                resp.raise_for_status()
                context[output_var] = base64.b64encode(resp.content).decode()
        except Exception as e:
            log.warning("tts_failed", error=str(e), **self._audit_fields(context))

    async def _exec_reranker(self, config: dict, context: dict) -> None:
        """對 knowledge_results（或任意 docs 變數）重新排序，結果寫回 output_variable。"""
        query_var = config.get("query_variable", "user_input")
        docs_var = config.get("docs_variable", "knowledge_results")
        output_var = config.get("output_variable") or docs_var
        top_n = max(1, int(config.get("top_n", 3)))
        threshold = float(config.get("threshold", 0.0))
        provider = config.get("provider", "cohere")

        query = str(context.get(query_var, ""))
        docs: list[dict] = context.get(docs_var, [])
        if not docs or not query:
            return

        contents = [d.get("content", "") for d in docs]
        reranked: list[dict] = []

        try:
            if provider == "cohere":
                api_key = config.get("api_key", "") or getattr(settings, "COHERE_API_KEY", "")
                model = config.get("model", "rerank-multilingual-v3.0")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.cohere.com/v2/rerank",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": model, "query": query, "documents": contents, "top_n": top_n},
                    )
                    resp.raise_for_status()
                    for r in resp.json().get("results", []):
                        score = r.get("relevance_score", 0.0)
                        if score >= threshold:
                            doc = dict(docs[r["index"]])
                            doc["rerank_score"] = score
                            reranked.append(doc)

            else:  # generic HTTP (BGE-Reranker / Cohere-compatible)
                base_url = config.get("base_url", "").rstrip("/")
                api_key = config.get("api_key", "")
                model = config.get("model", "bge-reranker-v2-m3")
                headers: dict = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{base_url}/rerank",
                        headers=headers,
                        json={"model": model, "query": query, "documents": contents, "top_n": top_n},
                    )
                    resp.raise_for_status()
                    for r in resp.json().get("results", []):
                        score = r.get("relevance_score", 0.0)
                        if score >= threshold:
                            doc = dict(docs[r["index"]])
                            doc["rerank_score"] = score
                            reranked.append(doc)

        except Exception as e:
            log.warning("workflow_reranker_failed", error=str(e), fallback="truncate", **self._audit_fields(context))
            reranked = docs[:top_n]

        context[output_var] = reranked

    async def _exec_parameter_extraction(self, config: dict, context: dict) -> dict:
        """從輸入文字中提取結構化參數並寫入 context。"""
        method = config.get("method", "llm")
        text = str(context.get(config.get("variable", "user_input"), ""))
        parameters: list[dict] = config.get("parameters", [])
        extracted: dict = {}

        if method == "regex":
            for param in parameters:
                name = param.get("name", "")
                pattern = param.get("pattern", "")
                group = int(param.get("group", 1))
                default = str(param.get("default", ""))
                if not name or not pattern:
                    continue
                try:
                    m = re.search(pattern, text)
                    if m:
                        try:
                            extracted[name] = m.group(group)
                        except IndexError:
                            extracted[name] = m.group(0)
                    else:
                        extracted[name] = default
                except Exception:
                    extracted[name] = default

        else:  # llm
            param_lines = "\n".join(
                "- {name}: {desc}（{req}，預設：{default}）".format(
                    name=p.get("name", ""),
                    desc=p.get("description", ""),
                    req="必填" if p.get("required") else "選填",
                    default=p.get("default", "null"),
                )
                for p in parameters
                if p.get("name")
            )
            param_names = [p["name"] for p in parameters if p.get("name")]
            example = "{" + ", ".join(f'"{n}": "..."' for n in param_names) + "}"
            system = config.get(
                "system_prompt",
                "你是一個參數提取助手。從使用者輸入中提取指定參數，以 JSON 格式回傳，不包含任何說明。",
            )
            prompt = (
                f"從以下文字提取參數：\n\n文字：{text}\n\n"
                f"需提取的參數：\n{param_lines}\n\n"
                f"直接回傳 JSON，格式範例：{example}\n若無法提取某參數，使用預設值。"
            )
            try:
                llm, model = self._build_llm_client(config)
                resp = await llm.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    stream=False,
                    temperature=0.0,
                    max_tokens=512,
                )
                raw = resp.choices[0].message.content.strip()
                # strip markdown code fences if the model wraps the JSON
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw.strip())
                extracted = json.loads(raw)
            except Exception as e:
                log.warning("parameter_extraction_llm_failed", error=str(e), **self._audit_fields(context))
                extracted = {p["name"]: str(p.get("default", "")) for p in parameters if p.get("name")}

        # write each extracted value into context
        for name, value in extracted.items():
            context[name] = str(value) if value is not None else ""

        # optionally persist the full JSON under a single variable
        output_var = config.get("output_variable", "")
        if output_var:
            context[output_var] = json.dumps(extracted, ensure_ascii=False)

        return extracted

    def _resolve_next_node_key(self, candidate: str | None) -> str | None:
        """確認 next_node_key 真的存在於本 workflow graph；不存在則回 None。

        防禦性：避免使用者誤填或從別的 workflow 複製貼上設定，導致跳到
        不存在的 node（會被 execute() 的 while 迴圈直接結束）。
        """
        if candidate and candidate in self.nodes:
            return candidate
        if candidate:
            log.warning(
                "intent_next_node_key_not_found",
                requested=candidate, workflow_nodes=list(self.nodes.keys()),
            )
        return None

    async def _exec_intent(self, config: dict, context: dict) -> tuple[str, str | None]:
        """意圖識別：keyword 模式做字串比對，llm 模式請 LLM 回傳意圖編號。"""
        method = config.get("method", "keyword")
        intents: list[dict] = config.get("intents", [])
        text = str(context.get(config.get("variable", "user_input"), ""))
        default_key: str | None = self._resolve_next_node_key(
            config.get("default_next_node_key")
        )

        if method == "keyword":
            for intent in intents:
                for kw in intent.get("keywords", []):
                    if kw and kw in text:
                        return (
                            intent.get("label", ""),
                            self._resolve_next_node_key(intent.get("next_node_key")),
                        )
            return "default", default_key

        # llm 模式
        intent_lines = "\n".join(
            f"{i + 1}. {intent.get('label', '')}：{intent.get('description', '')}"
            for i, intent in enumerate(intents)
        )
        system = config.get(
            "system_prompt",
            "你是一個意圖分類助手。根據使用者輸入，從清單中選出最符合的意圖編號。只回傳數字，不要解釋。",
        )
        prompt = f"使用者輸入：{text}\n\n意圖清單：\n{intent_lines}\n\n請回傳最符合的意圖編號（數字）："
        try:
            llm, model = self._build_llm_client(config)
            resp = await llm.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                stream=False,
                temperature=0.0,
                max_tokens=10,
            )
            raw = resp.choices[0].message.content.strip()
            digits = "".join(c for c in raw if c.isdigit())
            idx = int(digits) - 1 if digits else -1
            if 0 <= idx < len(intents):
                matched = intents[idx]
                return (
                    matched.get("label", ""),
                    self._resolve_next_node_key(matched.get("next_node_key")),
                )
        except Exception as e:
            log.warning("intent_llm_failed", error=str(e), **self._audit_fields(context))
        return "default", default_key

    async def _exec_loop(self, config: dict, context: dict) -> AsyncIterator[dict]:
        """執行 loop 節點：支援 count / list / while 三種模式。"""
        loop_type = config.get("loop_type", "count")
        max_iter = min(int(config.get("max_iterations", 10)), 50)
        body_nodes = config.get("body_nodes", [])
        item_var = config.get("item_variable", "item")

        if loop_type == "list":
            raw = context.get(config.get("list_variable", "items"), [])
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    raw = [s.strip() for s in raw.split(",") if s.strip()]
            items: list = raw if isinstance(raw, list) else []
            iter_count = min(len(items), max_iter)
        elif loop_type == "count":
            iter_count = min(int(config.get("count", 1)), max_iter)
            items = []
        else:  # while
            iter_count = max_iter
            items = []

        for i in range(iter_count):
            context["__loop_index__"] = i
            if loop_type == "list" and i < len(items):
                context[item_var] = items[i]
            context["__break__"] = False

            for body_node in body_nodes:
                if context.get("__break__"):
                    break
                bkey = body_node.get("node_key", f"body_{i}_{body_node.get('node_type','')}")
                btype = body_node.get("node_type", "")
                bcfg = body_node.get("config", {})
                if isinstance(bcfg, str):
                    bcfg = json.loads(bcfg)

                yield {"event": "node_start", "data": json.dumps({"node_key": bkey, "type": btype})}
                try:
                    if btype == "llm":
                        async for token in self._exec_llm(bcfg, context):
                            yield {"event": "token", "data": token}
                    elif btype == "knowledge_retrieval":
                        context["knowledge_results"] = await self._exec_knowledge(bcfg, context)
                    elif btype == "variable":
                        for asgn in bcfg.get("assignments", []):
                            name = asgn.get("name")
                            if name:
                                context[name] = self._render_template(asgn.get("value_expression", ""), context)
                    elif btype == "http_request":
                        context["http_response"] = await self._exec_http(bcfg, context)
                    elif btype == "answer":
                        content = self._render_template(bcfg.get("content_template", "{{llm_response}}"), context)
                        for char in content:
                            yield {"event": "token", "data": char}
                    elif btype == "loop_break":
                        if self._eval_condition(bcfg, context):
                            context["__break__"] = True
                except Exception as e:
                    log.error(
                        "loop_body_failed",
                        node_key=bkey, error=str(e),
                        **self._audit_fields(context),
                    )
                    yield {"event": "error", "data": json.dumps({"node_key": bkey, "error": str(e)})}
                yield {"event": "node_done", "data": json.dumps({"node_key": bkey})}

            if context.get("__break__"):
                break

    async def _exec_http(self, config: dict, context: dict) -> dict:
        """通用 HTTP 請求節點。

        若 config.forward_workspace_auth == True，自動把當前 workspace 的
        X-User-ID / X-User-Roles 注入 header（呼叫內部 staffKM 服務時用）。
        對外部 URL 預設不注入，避免洩漏內部憑證。
        """
        method = config.get("method", "GET").upper()
        url = self._render_template(config.get("url", ""), context)
        headers = dict(config.get("headers", {}) or {})
        if config.get("forward_workspace_auth"):
            headers.update(self._downstream_headers(context))
        body_str = self._render_template(config.get("body_template", ""), context)
        try:
            body = json.loads(body_str) if body_str else None
        except Exception:
            body = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, headers=headers, json=body)
            try:
                return resp.json()
            except Exception:
                return {"status": resp.status_code, "text": resp.text[:500]}

    # ─────────────────────────────────────────────────────────────────
    # M2-1：10 個新 workflow node executor（basic 版）
    # ─────────────────────────────────────────────────────────────────

    async def _exec_wait(self, config: dict, context: dict) -> None:
        """依 config.seconds 延遲；最多 60 秒避免阻塞 worker。"""
        import asyncio
        seconds = max(0.0, min(float(config.get("seconds", 5)), 60.0))
        await asyncio.sleep(seconds)

    async def _exec_switch(self, config: dict, context: dict) -> str | None:
        """多分支：依 variable 值對應 case.next_node_key，否則 default_next_node_key。
        回傳 next_key 讓主迴圈跳轉；找不到回 None（呼叫端 fallback）。"""
        var = config.get("variable", "user_input")
        value = str(context.get(var, ""))
        for case in config.get("cases", []) or []:
            match = case.get("match", "")
            if value == match or (match and match in value):
                return self._resolve_next_node_key(case.get("next_node_key"))
        return self._resolve_next_node_key(config.get("default_next_node_key"))

    async def _exec_map(self, config: dict, context: dict):
        """逐項處理：對 list_variable 中每個 item 跑 body_nodes（簡化版：
        僅支援 llm / variable / answer / http_request 子節點）。
        結果累積到 output_variable（list）。"""
        list_var = config.get("list_variable", "items")
        item_var = config.get("item_variable", "item")
        output_var = config.get("output_variable", "mapped")
        body_nodes = config.get("body_nodes", []) or []
        raw = context.get(list_var, [])
        if isinstance(raw, str):
            try: raw = json.loads(raw)
            except Exception: raw = [raw]
        items = list(raw) if isinstance(raw, (list, tuple)) else []
        if not items:
            context[output_var] = []
            return

        # M2 收尾-A：batch manager — 分塊並行（chunk_size 由 config 或 manager 預設）
        if self.workflow_manager == "batch":
            async for ev in self._exec_map_batched(
                items=items, item_var=item_var, output_var=output_var,
                body_nodes=body_nodes, context=context,
                chunk_size=int(config.get("batch_size", 5)),
            ):
                yield ev
            return

        results: list = []
        for idx, it in enumerate(items):
            context[item_var] = it
            context["__map_index__"] = idx
            for body_node in body_nodes:
                bcfg = body_node.get("config", {})
                if isinstance(bcfg, str):
                    try: bcfg = json.loads(bcfg)
                    except Exception: bcfg = {}
                btype = body_node.get("node_type", "")
                yield {"event": "map_step", "data": json.dumps({"index": idx, "type": btype})}
                try:
                    if btype == "llm":
                        async for token in self._exec_llm(bcfg, context):
                            yield {"event": "token", "data": token}
                    elif btype == "variable":
                        for asgn in bcfg.get("assignments", []):
                            n = asgn.get("name")
                            if n:
                                context[n] = self._render_template(asgn.get("value_expression", ""), context)
                    elif btype == "http_request":
                        context["http_response"] = await self._exec_http(bcfg, context)
                    elif btype == "answer":
                        content = self._render_template(bcfg.get("content_template", "{{llm_response}}"), context)
                        for ch in content:
                            yield {"event": "token", "data": ch}
                except Exception as e:
                    log.error("map_body_failed", index=idx, error=str(e), **self._audit_fields(context))
            # 收集當前 item 的處理結果（用 llm_response 或 answer 文字）
            results.append(context.get("llm_response") or context.get(item_var))
        context[output_var] = results

    async def _exec_map_batched(
        self, *, items: list, item_var: str, output_var: str,
        body_nodes: list, context: dict, chunk_size: int,
    ):
        """batch manager：把 items 切 chunk_size 一組，組內並行、組間順序。

        每個 item 拿到 context 的 shallow copy，避免並行寫衝突；
        結果按 input order 寫回 context[output_var]。
        """
        import asyncio

        async def _run_one(idx: int, it):
            local = dict(context)
            local[item_var] = it
            local["__map_index__"] = idx
            for body_node in body_nodes:
                bcfg = body_node.get("config", {})
                if isinstance(bcfg, str):
                    try: bcfg = json.loads(bcfg)
                    except Exception: bcfg = {}
                btype = body_node.get("node_type", "")
                try:
                    if btype == "llm":
                        # 並行模式下不 yield token（會交錯難讀）；收集成 llm_response
                        chunks = []
                        async for token in self._exec_llm(bcfg, local):
                            chunks.append(token)
                        local["llm_response"] = "".join(chunks) or local.get("llm_response", "")
                    elif btype == "variable":
                        for asgn in bcfg.get("assignments", []):
                            n = asgn.get("name")
                            if n:
                                local[n] = self._render_template(asgn.get("value_expression", ""), local)
                    elif btype == "http_request":
                        local["http_response"] = await self._exec_http(bcfg, local)
                    elif btype == "answer":
                        local["llm_response"] = self._render_template(
                            bcfg.get("content_template", "{{llm_response}}"), local,
                        )
                except Exception as e:
                    log.error("batch_body_failed", index=idx, error=str(e), **self._audit_fields(local))
            return local.get("llm_response") or local.get(item_var)

        total = len(items)
        results: list = [None] * total
        for chunk_start in range(0, total, chunk_size):
            chunk = list(enumerate(items))[chunk_start:chunk_start + chunk_size]
            yield {"event": "batch_chunk_start", "data": json.dumps(
                {"chunk_start": chunk_start, "size": len(chunk)},
            )}
            outs = await asyncio.gather(*[_run_one(i, it) for i, it in chunk])
            for (i, _), out in zip(chunk, outs):
                results[i] = out
            yield {"event": "batch_chunk_done", "data": json.dumps(
                {"chunk_start": chunk_start, "size": len(chunk)},
            )}
        context[output_var] = results

    async def _exec_reduce(self, config: dict, context: dict) -> None:
        """聚合運算：sum / count / concat / first / last。"""
        list_var = config.get("list_variable", "items")
        op = (config.get("op") or "sum").lower()
        output_var = config.get("output_variable", "total")
        raw = context.get(list_var, [])
        if isinstance(raw, str):
            try: raw = json.loads(raw)
            except Exception: raw = []
        items = list(raw) if isinstance(raw, (list, tuple)) else []

        if op == "sum":
            total = 0.0
            for it in items:
                try: total += float(it)
                except Exception: pass
            context[output_var] = total
        elif op == "count":
            context[output_var] = len(items)
        elif op == "concat":
            sep = config.get("separator", "\n")
            context[output_var] = sep.join(str(x) for x in items)
        elif op == "first":
            context[output_var] = items[0] if items else None
        elif op == "last":
            context[output_var] = items[-1] if items else None
        else:
            log.warning("reduce_unknown_op", op=op, **self._audit_fields(context))
            context[output_var] = None

    async def _exec_webhook(self, config: dict, context: dict) -> None:
        """Webhook trigger 節點：只 echo 已注入的 webhook_payload 到 output_variable。
        實際接收 webhook 由外部 endpoint 處理（後續 PR 加 /webhooks/{path}）。"""
        output_var = config.get("output_variable", "webhook_payload")
        # 若使用者已從觸發處塞了 payload 進 context，原樣保留；否則空 dict
        if output_var not in context:
            context[output_var] = context.get("webhook_payload", {})

    async def _exec_notify(self, config: dict, context: dict) -> None:
        """推播通知（in_app / email / slack）— 目前只 log + 寫入 context.notify_sent。
        實際發送通道整合（後續 PR）由 channel 分派至對應 worker。"""
        channel = config.get("channel", "in_app")
        target = context.get(config.get("target_var", "")) if config.get("target_var") else None
        message = self._render_template(config.get("template", ""), context)
        log.info(
            "notify_dispatch",
            channel=channel, target=str(target)[:64], message=message[:200],
            **self._audit_fields(context),
        )
        context["notify_sent"] = {"channel": channel, "target": target, "message": message}

    async def _exec_email(self, config: dict, context: dict) -> None:
        """Email 寄送節點 — 目前 stub：render subject + body，log 後寫 context.email_drafted。
        實際 SMTP 整合（後續 PR）由 application config 設定 SMTP server。"""
        to = str(context.get(config.get("to_var", "recipient_email"), ""))
        subject = self._render_template(config.get("subject_template", ""), context)
        body = self._render_template(config.get("body_template", ""), context)
        log.info(
            "email_drafted",
            to=to[:128], subject=subject[:128],
            **self._audit_fields(context),
        )
        context["email_drafted"] = {"to": to, "subject": subject, "body": body}

    async def _exec_schedule(self, config: dict, context: dict) -> None:
        """排程觸發節點：實際排程由 scheduler worker 註冊；本節點僅標記 metadata
        供 workflow 設定階段使用。執行期視為 no-op。"""
        cron = config.get("cron", "")
        tz = config.get("timezone", "Asia/Taipei")
        log.info(
            "schedule_node_visited",
            cron=cron, tz=tz,
            **self._audit_fields(context),
        )
        context["schedule_meta"] = {"cron": cron, "timezone": tz}

    async def _exec_transform(self, config: dict, context: dict) -> None:
        """資料轉換：把 input_variable 套用 expression 模板後寫 output_variable。
        expression 是 {{var}} 模板（沿用 _render_template），不執行 eval。"""
        input_var = config.get("input_variable", "input")
        output_var = config.get("output_variable", "transformed")
        expression = config.get("expression", "{{" + input_var + "}}")
        # 暫時把 input_var 值 alias 為 'input' 供 expression 引用
        bak = context.get("input")
        try:
            context["input"] = context.get(input_var, "")
            context[output_var] = self._render_template(expression, context)
        finally:
            if bak is None:
                context.pop("input", None)
            else:
                context["input"] = bak

    async def _exec_merge(self, config: dict, context: dict) -> None:
        """合併多個 source_variables 的值（list / dict / 字串都支援）到 output_variable。
        - 全 list → concat
        - 全 dict → 後者覆蓋前者（淺合併）
        - 其他 → 用 \\n 串接字串化值"""
        sources: list[str] = config.get("source_variables", []) or []
        output_var = config.get("output_variable", "merged")
        values = [context.get(s) for s in sources]
        values_nn = [v for v in values if v is not None]
        if not values_nn:
            context[output_var] = None
            return
        if all(isinstance(v, list) for v in values_nn):
            out: list = []
            for v in values_nn: out.extend(v)
            context[output_var] = out
        elif all(isinstance(v, dict) for v in values_nn):
            merged: dict = {}
            for v in values_nn: merged.update(v)
            context[output_var] = merged
        else:
            context[output_var] = "\n".join(str(v) for v in values_nn)
