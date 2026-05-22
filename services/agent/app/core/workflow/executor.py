"""Workflow Executor — 依 DAG 順序執行節點"""
import base64
import json
import re
import time
import uuid as _uuid
import httpx
import structlog
from typing import AsyncIterator, Any
from openai import AsyncOpenAI
from sqlalchemy import text
from app.config import settings
# v3.3：workflow LLM 節點接 metering（quota check + usage record + cost calc）
from app.core.metering import meter_llm_call, meter_media_call
from app.core.providers.base import BaseProvider, ChatRequest
from app.core.providers.openai_compat import OpenAICompatProvider
from staffkm_core.utils import database as _db

log = structlog.get_logger()


_VALID_MANAGERS = ("simple", "parallel", "retry", "batch", "sandbox")


class WorkflowPaused(Exception):
    """v3.5 P2：workflow 因 human_approval 暫停。

    dispatcher / resume worker 應捕捉本例外，將 run 標 'paused' 並寫 resume_node。
    """
    def __init__(self, node_key: str, approval_id: str):
        self.node_key = node_key
        self.approval_id = approval_id
        super().__init__(f"workflow paused at {node_key}, approval={approval_id}")


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
        application_id: str | None = None,  # v3.3：metering 歸帳到 application
        *,
        run_id: _uuid.UUID | str | None = None,  # v3.5 P1：寫 workflow_run_steps 用
        resume_from_node: str | None = None,  # v3.5 P2：resume worker 用，從此 node 的下一個 node 開始跑
        depth: int = 0,  # v3.5 P3：sub_workflow 巢狀深度，>3 raise 防無窮遞迴
        conversation_id: str | None = None,  # v3.8 P1：embedded workflow 跟 chat 對話歸因
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
        # v3.3：給 metering 用；caller (workflows.py / trigger_dispatcher) 應傳入
        self.application_id = application_id
        # v3.5 P1：run-level id（trigger dispatcher 帶入）+ step index 累計
        self.run_id = run_id
        self._step_idx: int = 0
        # v3.5 P2：resume worker 帶入；若設了，main loop 會從 resume_from_node 的下一個 node 開始
        self.resume_from_node = resume_from_node
        # v3.8 P1：conversation_id 給 meter call site 帶（chat-embedded workflow 才有意義；trigger-fired = None）
        self.conversation_id = conversation_id
        # v3.5 P3：sub_workflow 巢狀深度
        if depth > 3:
            raise RuntimeError(f"sub_workflow depth exceeded (>3): {depth}")
        self.depth = depth
        # 建立有向圖（key -> [key, ...]）
        self.children: dict[str, list[str]] = {n: [] for n in self.nodes}
        self.edge_conditions: dict[tuple, Any] = {}
        for edge in edges:
            src, tgt = edge["source_node_key"], edge["target_node_key"]
            if src in self.children:
                self.children[src].append(tgt)
            self.edge_conditions[(src, tgt)] = edge.get("condition")

    async def _record_step(
        self,
        *,
        node_key: str,
        node_type: str,
        input_data: Any,
        output_data: Any,
        status: str,
        error: str | None,
        attempts: int,
        latency_ms: int,
    ) -> None:
        """v3.5 P1：寫一筆 workflow_run_steps（run_id 未設或 db 未初始化則 noop）。"""
        if not self.run_id or not _db._session_factory:
            return

        def _truncate(d: Any) -> Any:
            try:
                s = json.dumps(d, ensure_ascii=False, default=str)
                if len(s) <= 4096:
                    return json.loads(s)
                return {"_truncated": True, "_size": len(s), "_preview": s[:3900]}
            except Exception:
                return {"_unserializable": True}

        try:
            async with _db._session_factory() as session:
                await session.execute(text("""
                    INSERT INTO workflow_run_steps (
                        run_id, step_index, node_key, node_type,
                        status, input_snapshot, output_snapshot,
                        error, attempts, latency_ms, finished_at
                    ) VALUES (
                        :rid, :idx, :nkey, :ntype, :status,
                        CAST(:inp AS jsonb), CAST(:out AS jsonb),
                        :err, :att, :lat, now()
                    )
                """), {
                    "rid": str(self.run_id),
                    "idx": self._step_idx,
                    "nkey": node_key,
                    "ntype": node_type,
                    "status": status,
                    "inp": json.dumps(_truncate(input_data), ensure_ascii=False),
                    "out": json.dumps(_truncate(output_data), ensure_ascii=False),
                    "err": (error[:1000] if error else None),
                    "att": attempts,
                    "lat": latency_ms,
                })
                await session.commit()
                self._step_idx += 1
        except Exception as e:
            log.warning("step_record_failed", run=str(self.run_id), node=node_key, error=str(e))

    async def _exec_human_approval(self, config: dict, context: dict, current_key: str) -> None:
        """v3.5 P2：寫一筆 workflow_approvals (pending) 並 raise WorkflowPaused。

        config:
          payload_template: 給 admin 預覽的 context（用 self._render_template 渲染）
          approver_role:    'admin' / 'manager'（v3.5 只用 admin）
        """
        if not self.run_id or not _db._session_factory:
            # 沒 persistence 環境 → skip approval、直接通過（dev/unit-test 友善）
            log.warning("human_approval_skipped_no_persistence", node=current_key)
            return

        payload_template = config.get("payload_template", "") if isinstance(config, dict) else ""
        try:
            rendered = self._render_template(payload_template, context) if payload_template else ""
        except Exception:
            rendered = payload_template

        payload = {
            "context_preview": str(rendered)[:2000],
            "node_config": config,
        }

        try:
            async with _db._session_factory() as session:
                r = await session.execute(text("""
                    INSERT INTO workflow_approvals (
                        run_id, workspace_id, node_key, status, payload
                    ) VALUES (:rid, :ws, :nkey, 'pending', CAST(:pl AS jsonb))
                    RETURNING id
                """), {
                    "rid": str(self.run_id),
                    "ws": str(self.workspace_id),
                    "nkey": current_key,
                    "pl": json.dumps(payload, ensure_ascii=False, default=str),
                })
                approval_id = str(r.scalar_one())
                await session.commit()
        except Exception as e:
            log.error("human_approval_insert_failed", node=current_key, error=str(e))
            raise

        log.info("human_approval_pending", run=str(self.run_id),
                 node=current_key, approval_id=approval_id)
        raise WorkflowPaused(node_key=current_key, approval_id=approval_id)

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
        # v3.5 P2：若 resume_from_node 有設，從該 node 的下一個（edges 中 source==resume_from_node）開始
        if self.resume_from_node:
            current_key = next(
                (e["target_node_key"] for e in self.edges
                 if e.get("source_node_key") == self.resume_from_node),
                None,
            )
            if not current_key:
                log.warning("resume_node_no_next", node=self.resume_from_node)
                yield {"event": "done", "data": "[DONE]"}
                return
        else:
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

        # M2-2 → M2 收尾：parallel / batch 已有真實語義；
        # sandbox 在 M2 收尾提供 subprocess + rlimit 隔離（M4 升 nsjail / firecracker）
        if self.workflow_manager == "sandbox":
            log.info(
                "workflow_manager_sandbox",
                note="shell 節點將透過 SubprocessSandbox 執行（rlimit + timeout）。",
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

            # v5.3: node disabled flag — 前端 NodeConfigPanel toggle
            # 略過執行但保留 graph 流向（next_key 用第一個 edge）
            if node.get("disabled") is True:
                yield {"event": "node_skipped", "data": json.dumps({"node_key": current_key, "type": node_type, "reason": "disabled"})}
                # 找下一節點：第一個 outgoing edge
                next_edge = next((e for e in self.edges if e.get("source_node_key") == current_key), None)
                current_key = next_edge.get("target_node_key") if next_edge else None
                continue

            yield {"event": "node_start", "data": json.dumps({"node_key": current_key, "type": node_type})}

            next_key = None
            # v3.5 P1：step 追蹤
            _step_started = time.monotonic()
            _step_status = "ok"
            _step_error: str | None = None
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

                # ── MaxKB v2 多模態擴充（v5.3 prep）────────────────
                elif node_type == "video_understand":
                    async for token in self._exec_video_understand(config, context):
                        yield {"event": "token", "data": token}

                elif node_type == "text_to_video":
                    await self._exec_text_to_video(config, context)

                elif node_type == "image_to_video":
                    await self._exec_image_to_video(config, context)

                elif node_type == "document_tag_retrieval":
                    results = await self._exec_document_tag_retrieval(config, context)
                    context["knowledge_results"] = results

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

                # ── M2 收尾：sandbox 隔離下的 shell 節點 ───────────────
                elif node_type == "shell":
                    async for ev in self._exec_shell(config, context):
                        yield ev

                # ── v5.10.8：code 節點 — sandbox 跑 def run(**kwargs)（對標 MaxKB 函數庫）──
                elif node_type == "code":
                    async for ev in self._exec_code_node(config, context):
                        yield ev

                # ── v2.1 / RFC-013：寫入 workflow KB ───────────────
                elif node_type == "kb_writer":
                    async for ev in self._exec_kb_writer(config, context):
                        yield ev

                # ── v3.5 P2：human_approval — 寫 pending row + raise WorkflowPaused ──
                elif node_type == "human_approval":
                    await self._exec_human_approval(config, context, current_key)

                # ── v3.5 P3：sub_workflow — 呼叫另一個 application 的 workflow ──
                elif node_type == "sub_workflow":
                    async for ev in self._exec_sub_workflow(config, context):
                        yield ev

                # ── v4.3 Theme C：plugin node fallback ─────────────────────────
                # TODO (v4.4): 從 app.core.plugin_loader.get_plugin_node 取 BaseNode
                # 實例，注入 PluginContext(workspace_id, user_id, session_factory)，
                # 呼叫 await pnode.execute(config, ctx, context)；dict 結果 update
                # 回 context。本 PR 暫不實接以免 break workflow runtime；plugin SDK
                # 已可在 lifespan 內 load 並透過 /api/v1/admin/plugins 列出。
                # else:
                #     from app.core.plugin_loader import get_plugin_node
                #     pnode = get_plugin_node(node_type)
                #     if pnode:
                #         from staffkm_plugin_sdk.base import PluginContext
                #         pctx = PluginContext(
                #             workspace_id=str(self.workspace_id),
                #             user_id=str(self.user_id) if self.user_id else None,
                #             session_factory=lambda: _db._session_factory,
                #         )
                #         _result = await pnode.execute(config, pctx, context)
                #         if isinstance(_result, dict):
                #             context.update(_result)

            except WorkflowPaused:
                # v3.5 P2：暫停而非錯誤；寫一筆 paused step 後 re-raise，caller 處理 run.status
                await self._record_step(
                    node_key=current_key, node_type=node_type,
                    input_data=config, output_data=None,
                    status="paused", error=None,
                    attempts=1,
                    latency_ms=int((time.monotonic() - _step_started) * 1000),
                )
                yield {"event": "paused", "data": json.dumps({"node_key": current_key})}
                raise
            except Exception as e:
                _step_status = "error"
                _step_error = str(e)
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
                    # 寫一筆 retry step（status=retry）後重跑
                    await self._record_step(
                        node_key=current_key, node_type=node_type,
                        input_data=config,
                        output_data=None,
                        status="retry",
                        error=_step_error,
                        attempts=attempts,
                        latency_ms=int((time.monotonic() - _step_started) * 1000),
                    )
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

            # v3.5 P1：寫 step（成功/失敗都寫，retry 的已在上面寫過並 continue）
            _node_output_var = (config or {}).get("output_variable") if isinstance(config, dict) else None
            _node_output = context.get(_node_output_var) if _node_output_var else None
            await self._record_step(
                node_key=current_key,
                node_type=node_type,
                input_data=config,
                output_data=_node_output,
                status=_step_status,
                error=_step_error,
                attempts=_node_attempts.get(current_key, 1),
                latency_ms=int((time.monotonic() - _step_started) * 1000),
            )

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

    def _build_llm_provider(self, config: dict) -> tuple[BaseProvider, str]:
        """v3.3：回傳 BaseProvider 取代 raw AsyncOpenAI；同樣鎖系統 model（RFC-005）。

        executor 一律走 openai_compat — 對 OpenAI / Ollama / Together / Groq /
        DeepSeek / Moonshot / 自架 vLLM 都通。其他真正 native protocol（Anthropic /
        Bedrock / Gemini / VertexAI）後續 v3.4 再走它們的 adapter。
        """
        base_url = settings.LLM_BASE_URL
        api_key = settings.LLM_API_KEY or "dummy"
        model = settings.LLM_MODEL
        node_model = config.get("model")
        if node_model and node_model != model:
            log.warning(
                "llm_model_override_blocked",
                requested=node_model, enforced=model,
                reason="RFC-005 onprem-llm-first 政策：僅允許單一系統 LLM 模型",
            )
        return OpenAICompatProvider(api_key=api_key, base_url=base_url), model

    @staticmethod
    def _estimate_tokens_text(text: str) -> int:
        """粗估 token 數。中英混合常見 ratio: 1 token ≈ 4 chars。
        精準度不必高 — 用於 quota / 計費估算的下限。
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _estimate_tokens_messages(self, messages: list[dict]) -> int:
        """粗估 messages 總 token：把每則 content 串起來估，加上每則 ~4 token overhead。"""
        total = 0
        for m in messages or []:
            c = m.get("content", "")
            if isinstance(c, str):
                total += self._estimate_tokens_text(c)
            elif isinstance(c, list):
                # vision/multimodal: 只算 text part；image 部分由 provider 計
                for part in c:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += self._estimate_tokens_text(part.get("text", ""))
            total += 4  # role + delimiter overhead
        return total

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

        # v3.3：改走 BaseProvider + meter_llm_call（quota check + usage record）
        provider, model = self._build_llm_provider(config)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        req = ChatRequest(
            model=model,
            messages=messages,
            stream=True,
            temperature=float(config.get("temperature", settings.LLM_TEMPERATURE)),
            max_tokens=int(config.get("max_tokens", settings.LLM_MAX_TOKENS)),
        )
        prompt_tokens_est = self._estimate_tokens_messages(messages)
        full_response = ""

        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            # 沒 DB / 無 workspace 上下文：退化為純串流（不計費）
            try:
                async for delta in provider.chat_stream(req):
                    if delta:
                        full_response += delta
                        yield delta
            except Exception as e:
                log.error("workflow_llm_failed", error=str(e), **self._audit_fields(context))
                yield f"\n\n錯誤：LLM 呼叫失敗：{e}"
            context["llm_response"] = full_response
            return

        async with sess_factory() as meter_session:
            try:
                async with meter_llm_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type="openai_compat",
                    model=model,
                    feature="workflow",
                    conversation_id=self.conversation_id,
                ) as meter:
                    try:
                        async for delta in provider.chat_stream(req):
                            if delta:
                                full_response += delta
                                yield delta
                    finally:
                        meter.record(
                            prompt_tokens=prompt_tokens_est,
                            completion_tokens=self._estimate_tokens_text(full_response),
                        )
            except Exception as e:
                # QuotaExceeded 也在此被攔；交由 caller (workflows.py / dispatcher) 處理
                from app.core.usage import QuotaExceeded
                if isinstance(e, QuotaExceeded):
                    raise
                log.error("workflow_llm_failed", error=str(e), **self._audit_fields(context))
                yield f"\n\n錯誤：LLM 呼叫失敗：{e}"
        context["llm_response"] = full_response

    async def _chat_with_meter(
        self, req: ChatRequest, context: dict, *, fallback_prompt_tokens: int = 0
    ) -> str:
        """v3.3 non-streaming chat helper：自動接 meter_llm_call。

        - 有 DB + workspace 上下文 → quota check + usage record
        - 沒有 → 直接呼叫 provider.chat()
        - QuotaExceeded 不吞 — 由 caller 處理
        """
        provider = OpenAICompatProvider(
            api_key=settings.LLM_API_KEY or "dummy",
            base_url=settings.LLM_BASE_URL,
        )
        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            resp = await provider.chat(req)
            return resp.text

        async with sess_factory() as meter_session:
            async with meter_llm_call(
                meter_session,
                workspace_id=self.workspace_id,
                user_id=context.get("_user_id") or self.user_id,
                application_id=self.application_id,
                provider_type="openai_compat",
                model=req.model,
                feature="workflow",
                conversation_id=self.conversation_id,
            ) as meter:
                resp = await provider.chat(req)
                # 優先用 provider 回的真實 token；否則用 fallback 估算
                meter.record(
                    prompt_tokens=resp.prompt_tokens or fallback_prompt_tokens,
                    completion_tokens=(
                        resp.completion_tokens
                        or self._estimate_tokens_text(resp.text)
                    ),
                )
                return resp.text

    def _eval_condition(self, config: dict, context: dict) -> bool:
        variable = config.get("variable", "")
        operator = config.get("operator", "contains")
        value = config.get("value", "")
        actual = str(context.get(variable, ""))
        if operator == "contains":
            return value in actual
        elif operator == "equals":
            return actual == value
        elif operator == "not_equal":
            # MaxKB v2：!= 反向
            return actual != value
        elif operator == "not_empty":
            return bool(actual.strip())
        elif operator == "is_empty":
            return not bool(actual.strip())
        elif operator == "regex_match":
            # MaxKB v2：re.search 半匹配；pattern invalid 視為不匹配
            try:
                return bool(re.search(str(value), actual))
            except re.error as e:
                log.warning("condition_regex_invalid", pattern=str(value), error=str(e))
                return False
        elif operator == "wildcard_match":
            # MaxKB v2：fnmatch（* / ? / [seq]）— lazy import 避免污染 module level
            import fnmatch
            return fnmatch.fnmatch(actual, str(value))
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
        """表單節點：填入預設值並發送 form_request 事件，使前端可渲染表單。

        v2.9：field.type 接受 'tree_select'（schema: options=[{value,label,children:[…]}]）。
        runtime 不做特別處理（前端 render + 收 leaf value），但 schema validation
        通過 — 即 unknown type 不再 reject。
        """
        fields: list[dict] = config.get("fields", [])
        _ALLOWED_FIELD_TYPES = {
            "text", "textarea", "number", "select", "checkbox", "radio",
            "date", "tree_select",  # v2.9
        }
        missing: list[str] = []

        for field in fields:
            name = field.get("name", "")
            if not name:
                continue
            ftype = field.get("type", "text")
            if ftype not in _ALLOWED_FIELD_TYPES:
                log.warning(
                    "form_field_unknown_type", field=name, type=ftype,
                    **self._audit_fields(context),
                )
            if ftype == "tree_select":
                # tree_select 的 options 是遞迴 list[{value,label,children:[]}]；
                # 此處只做 schema 在場性檢查（前端負責 render + 收 leaf value）
                opts = field.get("options", [])
                if not isinstance(opts, list):
                    log.warning(
                        "form_tree_select_invalid_options", field=name,
                        **self._audit_fields(context),
                    )
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

        # v3.3：vision 走 openai_compat provider + metering（text portion 計費）
        base_url = (config.get("base_url") or "").rstrip("/") or None
        provider = OpenAICompatProvider(api_key=api_key, base_url=base_url)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ]},
        ]
        req = ChatRequest(
            model=model, messages=messages, stream=True,
            temperature=temperature, max_tokens=max_tokens,
        )
        prompt_tokens_est = self._estimate_tokens_messages(messages)
        full_response = ""

        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            try:
                async for delta in provider.chat_stream(req):
                    if delta:
                        full_response += delta
                        yield delta
            except Exception as e:
                log.error("image_understand_failed", error=str(e), **self._audit_fields(context))
                yield f"\n\n錯誤：圖像分析失敗：{e}"
            context[output_var] = full_response
            return

        async with sess_factory() as meter_session:
            try:
                async with meter_llm_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type="openai_compat",
                    model=model,
                    feature="workflow",
                    conversation_id=self.conversation_id,
                ) as meter:
                    try:
                        async for delta in provider.chat_stream(req):
                            if delta:
                                full_response += delta
                                yield delta
                    finally:
                        meter.record(
                            prompt_tokens=prompt_tokens_est,
                            completion_tokens=self._estimate_tokens_text(full_response),
                        )
            except Exception as e:
                from app.core.usage import QuotaExceeded
                if isinstance(e, QuotaExceeded):
                    raise
                log.error("image_understand_failed", error=str(e), **self._audit_fields(context))
                yield f"\n\n錯誤：圖像分析失敗：{e}"
        context[output_var] = full_response

    async def _exec_image_generate(self, config: dict, context: dict) -> None:
        """圖像生成：呼叫 DALL-E 相容 API，將圖片 URL 或 Base64 存入 context。

        v3.4 P1: metered via meter_media_call（per-image pricing）。
        """
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

        async def _do_generate() -> None:
            llm = AsyncOpenAI(**client_kwargs)
            resp = await llm.images.generate(**gen_kwargs)
            first = resp.data[0]
            context[output_var] = (first.b64_json or "") if output_type == "base64" else (first.url or "")
            if revised_var and first.revised_prompt:
                context[revised_var] = first.revised_prompt

        # v3.4 P1: 接 meter_media_call（per-image）；無 session/workspace 時 graceful degrade
        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            try:
                await _do_generate()
            except Exception as e:
                log.error("image_generate_failed", error=str(e), **self._audit_fields(context))
            return

        try:
            async with sess_factory() as meter_session:
                async with meter_media_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type="openai",
                    model=model,
                    unit_type="image",
                    feature="image",
                    conversation_id=self.conversation_id,
                ) as meter:
                    try:
                        await _do_generate()
                    finally:
                        meter.record(unit_count=n)
        except Exception as e:
            from app.core.usage import QuotaExceeded
            if isinstance(e, QuotaExceeded):
                raise
            log.error("image_generate_failed", error=str(e), **self._audit_fields(context))

    # ─────────────────────────────────────────────────────────────────
    # MaxKB v2 多模態擴充（v5.3 prep）：video understand / t2v / i2v / tag retrieval
    # ─────────────────────────────────────────────────────────────────

    async def _exec_video_understand(self, config: dict, context: dict) -> AsyncIterator[str]:
        """影片理解：類 image_understand，差別在 input 是 video URL。

        - 用 OpenAI vision messages 格式但 part type='video_url'（Gemini 支援）。
        - 若 provider 不接受（exception / 4xx），fallback 改傳 text 'video at {url}'。
        - thinking_process=True 時 system prompt 多帶 step-by-step instruction（v2.8）。
        - 走 meter_llm_call。
        """
        input_var = config.get("input_variable", "video_url")
        output_var = config.get("output_variable", "video_description")
        video_url = str(context.get(input_var, ""))
        if not video_url:
            return

        api_key = config.get("api_key", "") or settings.OPENAI_API_KEY
        model = config.get("model", "gemini-1.5-pro")
        base_system = config.get("system_prompt", "你是一個影片分析助手。")
        if config.get("thinking_process", False):
            # MaxKB v2.8：step-by-step thinking
            base_system = base_system + "\n請以 step-by-step 的方式逐步分析後再給結論。"
        prompt = self._render_template(config.get("prompt", "請詳細描述這部影片的內容。"), context)
        max_tokens = int(config.get("max_tokens", 1024))
        temperature = float(config.get("temperature", 0.1))

        base_url = (config.get("base_url") or "").rstrip("/") or None
        provider = OpenAICompatProvider(api_key=api_key, base_url=base_url)

        def _build_messages(use_video_url: bool) -> list[dict]:
            if use_video_url:
                return [
                    {"role": "system", "content": base_system},
                    {"role": "user", "content": [
                        {"type": "video_url", "video_url": {"url": video_url}},
                        {"type": "text", "text": prompt},
                    ]},
                ]
            # fallback：純 text
            return [
                {"role": "system", "content": base_system},
                {"role": "user", "content": f"{prompt}\n\nvideo at {video_url}"},
            ]

        messages = _build_messages(use_video_url=True)
        req = ChatRequest(
            model=model, messages=messages, stream=True,
            temperature=temperature, max_tokens=max_tokens,
        )
        prompt_tokens_est = self._estimate_tokens_messages(messages)
        full_response = ""

        async def _stream_with_fallback() -> AsyncIterator[str]:
            """嘗試 video_url；若 provider 不支援，改 fallback messages 重跑。"""
            nonlocal full_response, messages, req
            try:
                async for delta in provider.chat_stream(req):
                    if delta:
                        full_response += delta
                        yield delta
            except Exception as primary_err:
                # 多數 OpenAI-compat 端點還不認 video_url；fallback 用 text
                log.warning(
                    "video_understand_fallback_to_text",
                    error=str(primary_err), **self._audit_fields(context),
                )
                messages = _build_messages(use_video_url=False)
                req2 = ChatRequest(
                    model=model, messages=messages, stream=True,
                    temperature=temperature, max_tokens=max_tokens,
                )
                async for delta in provider.chat_stream(req2):
                    if delta:
                        full_response += delta
                        yield delta

        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            try:
                async for delta in _stream_with_fallback():
                    yield delta
            except Exception as e:
                log.error("video_understand_failed", error=str(e), **self._audit_fields(context))
                yield f"\n\n錯誤：影片分析失敗：{e}"
            context[output_var] = full_response
            return

        async with sess_factory() as meter_session:
            try:
                async with meter_llm_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type="openai_compat",
                    model=model,
                    feature="workflow",
                    conversation_id=self.conversation_id,
                ) as meter:
                    try:
                        async for delta in _stream_with_fallback():
                            yield delta
                    finally:
                        meter.record(
                            prompt_tokens=prompt_tokens_est,
                            completion_tokens=self._estimate_tokens_text(full_response),
                        )
            except Exception as e:
                from app.core.usage import QuotaExceeded
                if isinstance(e, QuotaExceeded):
                    raise
                log.error("video_understand_failed", error=str(e), **self._audit_fields(context))
                yield f"\n\n錯誤：影片分析失敗：{e}"
        context[output_var] = full_response

    async def _exec_text_to_video(self, config: dict, context: dict) -> None:
        """文生影片：Bailian Wan 2.1（dashscope async API）。

        OpenAI-compat 端點不支援 video gen，需走 dashscope native：
          POST /api/v1/services/aigc/video-generation/video-synthesis
          (X-DashScope-Async: enable) → task_id → 輪詢 /api/v1/tasks/{task_id}
        走 meter_media_call(provider_type='bailian', unit_type='call')。
        """
        await self._exec_bailian_video(config, context, mode="t2v")

    async def _exec_image_to_video(self, config: dict, context: dict) -> None:
        """圖生影片：Bailian Wan 2.1 i2v-turbo；input 加 image_url 起始幀 + 可選 last_frame_url。"""
        await self._exec_bailian_video(config, context, mode="i2v")

    async def _exec_bailian_video(self, config: dict, context: dict, *, mode: str) -> None:
        """Bailian Wan video generation 共用 dispatcher（t2v / i2v）。"""
        output_var = config.get("output_variable", "generated_video_url")
        prompt = self._render_template(config.get("prompt_template", "{{user_input}}"), context)
        api_key = config.get("api_key", "") or getattr(settings, "DASHSCOPE_API_KEY", "") or ""
        if not api_key:
            log.error("bailian_video_no_api_key", mode=mode, **self._audit_fields(context))
            context[output_var] = ""
            return

        size = config.get("size", "1280*720")
        timeout_total = float(config.get("timeout", 300.0))
        poll_interval = float(config.get("poll_interval", 5.0))

        if mode == "t2v":
            model = config.get("model", "wan2.1-t2v-turbo")
            input_payload: dict = {"prompt": prompt}
        else:  # i2v
            model = config.get("model", "wan2.1-i2v-turbo")
            image_url_var = config.get("image_variable", "image_url")
            image_url = str(context.get(image_url_var, "") or config.get("image_url", ""))
            if not image_url:
                log.error("bailian_i2v_no_image", **self._audit_fields(context))
                context[output_var] = ""
                return
            input_payload = {"prompt": prompt, "image_url": image_url}
            last_frame_var = config.get("last_frame_variable", "last_frame_url")
            last_frame = str(context.get(last_frame_var, "") or config.get("last_frame_url", ""))
            if last_frame:
                input_payload["last_frame_url"] = last_frame

        submit_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
        submit_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": model,
            "input": input_payload,
            "parameters": {"size": size},
        }

        async def _do_generate() -> None:
            import asyncio
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(submit_url, headers=submit_headers, json=payload)
                r.raise_for_status()
                data = r.json()
                task_id = (data.get("output", {}) or {}).get("task_id") or data.get("task_id")
                if not task_id:
                    raise RuntimeError(f"bailian video submit no task_id: {data}")

                poll_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
                poll_headers = {"Authorization": f"Bearer {api_key}"}
                start = time.monotonic()
                while True:
                    if time.monotonic() - start > timeout_total:
                        raise TimeoutError(f"bailian video task {task_id} timeout > {timeout_total}s")
                    pr = await client.get(poll_url, headers=poll_headers)
                    pr.raise_for_status()
                    pdata = pr.json()
                    output = pdata.get("output", {}) or {}
                    status = (output.get("task_status") or "").upper()
                    if status == "SUCCEEDED":
                        video_url = output.get("video_url") or output.get("results", [{}])[0].get("url", "")
                        context[output_var] = video_url
                        return
                    if status in ("FAILED", "CANCELED", "UNKNOWN"):
                        raise RuntimeError(f"bailian video task {task_id} {status}: {output}")
                    await asyncio.sleep(poll_interval)

        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            try:
                await _do_generate()
            except Exception as e:
                log.error("bailian_video_failed", mode=mode, error=str(e), **self._audit_fields(context))
                context[output_var] = ""
            return

        try:
            async with sess_factory() as meter_session:
                async with meter_media_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type="bailian",
                    model=model,
                    unit_type="call",
                    feature="video",
                    conversation_id=self.conversation_id,
                ) as meter:
                    try:
                        await _do_generate()
                    finally:
                        meter.record(unit_count=1)
        except Exception as e:
            from app.core.usage import QuotaExceeded
            if isinstance(e, QuotaExceeded):
                raise
            log.error("bailian_video_failed", mode=mode, error=str(e), **self._audit_fields(context))
            context[output_var] = ""

    async def _exec_document_tag_retrieval(self, config: dict, context: dict) -> list[dict]:
        """tag-filtered 知識庫檢索：在 _exec_knowledge 基礎上多帶 tags + tag_match_mode。

        v5.10.11：knowledge service /search 已真正支援 tags / tag_match_mode
        （'any' = jsonb_exists_any、'all' = @>），依文件 tags 過濾命中段落。
        """
        kb_ids = config.get("kb_ids", [])
        if not kb_ids:
            return []
        tags = config.get("tags", []) or []
        match_mode = config.get("match_mode", "any")
        if match_mode not in ("any", "all"):
            match_mode = "any"
        try:
            payload = {
                "query": context.get("user_input", ""),
                "kb_ids": kb_ids,
                "top_k": config.get("top_k", 5),
                "similarity_threshold": config.get("similarity_threshold", 0.45),
                "tags": tags,
                "tag_match_mode": match_mode,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    self._knowledge_url(context, "search"),
                    json=payload,
                    headers=self._downstream_headers(context),
                )
                if resp.status_code == 200:
                    return resp.json().get("data", {}).get("citations", [])
                log.warning(
                    "workflow_document_tag_retrieval_non_200",
                    status=resp.status_code, body=resp.text[:200],
                    **self._audit_fields(context),
                )
        except Exception as e:
            log.warning(
                "workflow_document_tag_retrieval_failed",
                error=str(e), **self._audit_fields(context),
            )
        return []

    async def _exec_stt(self, config: dict, context: dict) -> None:
        """Speech-to-Text：呼叫 Whisper 相容 API，轉錄音訊後寫入 context.

        v3.4 P1: metered via meter_media_call（per-second pricing）。
        實際秒數從 audio_bytes 粗估（32 kbps 假設），無法精準時就以此為記帳基準。
        """
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

        async def _do_stt() -> float:
            """執行 STT，回傳粗估的 audio 秒數（用於計費）。"""
            nonlocal_state: dict = {}
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
            # 粗估秒數：bytes / (32 kbps / 8) = bytes / 4000；最少 1 秒
            return max(1.0, len(audio_bytes) / 4000.0)

        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            try:
                await _do_stt()
            except Exception as e:
                log.warning("stt_failed", error=str(e), **self._audit_fields(context))
                context[output_var] = ""
            return

        try:
            async with sess_factory() as meter_session:
                async with meter_media_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type="openai",
                    model=model,
                    unit_type="second",
                    feature="stt",
                    conversation_id=self.conversation_id,
                ) as meter:
                    duration = 0.0
                    try:
                        duration = await _do_stt()
                    finally:
                        meter.record(unit_count=duration)
        except Exception as e:
            from app.core.usage import QuotaExceeded
            if isinstance(e, QuotaExceeded):
                raise
            log.warning("stt_failed", error=str(e), **self._audit_fields(context))
            context[output_var] = ""

    async def _exec_tts(self, config: dict, context: dict) -> None:
        """Text-to-Speech：呼叫 OpenAI TTS 相容 API，將文字轉為 base64 音訊後寫入 context.

        v3.4 P1: metered via meter_media_call（per-character pricing）。
        """
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

        async def _do_tts() -> None:
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

        text_len = float(len(text))
        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            try:
                await _do_tts()
            except Exception as e:
                log.warning("tts_failed", error=str(e), **self._audit_fields(context))
            return

        try:
            async with sess_factory() as meter_session:
                async with meter_media_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type="openai",
                    model=model,
                    unit_type="char",
                    feature="tts",
                    conversation_id=self.conversation_id,
                ) as meter:
                    try:
                        await _do_tts()
                    finally:
                        meter.record(unit_count=text_len)
        except Exception as e:
            from app.core.usage import QuotaExceeded
            if isinstance(e, QuotaExceeded):
                raise
            log.warning("tts_failed", error=str(e), **self._audit_fields(context))

    async def _exec_reranker(self, config: dict, context: dict) -> None:
        """對 knowledge_results（或任意 docs 變數）重新排序，結果寫回 output_variable。

        v3.4 P1: metered via meter_media_call（per-call pricing；cohere = $0.001/call、self-host = 0）。
        """
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
        if provider == "cohere":
            model = config.get("model", "rerank-multilingual-v3.0")
        else:
            model = config.get("model", "bge-reranker-v2-m3")

        async def _do_rerank() -> list[dict]:
            out: list[dict] = []
            if provider == "cohere":
                api_key = config.get("api_key", "") or getattr(settings, "COHERE_API_KEY", "")
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
                            out.append(doc)
            else:  # generic HTTP (BGE-Reranker / Cohere-compatible)
                base_url = config.get("base_url", "").rstrip("/")
                api_key = config.get("api_key", "")
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
                            out.append(doc)
            return out

        reranked: list[dict] = []
        sess_factory = _db._session_factory
        if sess_factory is None or not self.workspace_id:
            try:
                reranked = await _do_rerank()
            except Exception as e:
                log.warning("workflow_reranker_failed", error=str(e), fallback="truncate", **self._audit_fields(context))
                reranked = docs[:top_n]
            context[output_var] = reranked
            return

        try:
            async with sess_factory() as meter_session:
                async with meter_media_call(
                    meter_session,
                    workspace_id=self.workspace_id,
                    user_id=context.get("_user_id") or self.user_id,
                    application_id=self.application_id,
                    provider_type=provider,
                    model=model,
                    unit_type="call",
                    feature="rerank",
                    conversation_id=self.conversation_id,
                ) as meter:
                    try:
                        reranked = await _do_rerank()
                    finally:
                        meter.record(unit_count=1)
        except Exception as e:
            from app.core.usage import QuotaExceeded
            if isinstance(e, QuotaExceeded):
                raise
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
                # v3.3：改走 BaseProvider + meter_llm_call
                provider, model = self._build_llm_provider(config)
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ]
                req = ChatRequest(
                    model=model, messages=messages, stream=False,
                    temperature=0.0, max_tokens=512,
                )
                raw = await self._chat_with_meter(req, context, fallback_prompt_tokens=self._estimate_tokens_messages(messages))
                # strip markdown code fences if the model wraps the JSON
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw.strip())
                extracted = json.loads(raw)
            except Exception as e:
                from app.core.usage import QuotaExceeded
                if isinstance(e, QuotaExceeded):
                    raise
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
            # v3.3：改走 BaseProvider + meter_llm_call
            provider, model = self._build_llm_provider(config)
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            req = ChatRequest(
                model=model, messages=messages, stream=False,
                temperature=0.0, max_tokens=10,
            )
            raw = (await self._chat_with_meter(
                req, context,
                fallback_prompt_tokens=self._estimate_tokens_messages(messages),
            )).strip()
            digits = "".join(c for c in raw if c.isdigit())
            idx = int(digits) - 1 if digits else -1
            if 0 <= idx < len(intents):
                matched = intents[idx]
                return (
                    matched.get("label", ""),
                    self._resolve_next_node_key(matched.get("next_node_key")),
                )
        except Exception as e:
            from app.core.usage import QuotaExceeded
            if isinstance(e, QuotaExceeded):
                raise
            log.warning("intent_llm_failed", error=str(e), **self._audit_fields(context))
        return "default", default_key

    async def _exec_loop(self, config: dict, context: dict) -> AsyncIterator[dict]:
        """執行 loop 節點：支援 count / list / while 三種模式。

        v2.9 新增 infinite 模式：config.infinite=True 時跑到 break condition 或達
        config.max_iterations（safety limit，預設 100）。為了 backward compat，
        非 infinite 走原邏輯（max_iter clamp 在 50）。
        """
        loop_type = config.get("loop_type", "count")
        infinite = bool(config.get("infinite", False))
        body_nodes = config.get("body_nodes", [])
        item_var = config.get("item_variable", "item")

        if infinite:
            # MaxKB v2.9：infinite mode — 由 break condition 終止，safety limit 預設 100
            safety_limit = max(1, int(config.get("max_iterations", 100)))
            iter_count = safety_limit
            items = []
        else:
            max_iter = min(int(config.get("max_iterations", 10)), 50)
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
            safety_limit = iter_count

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
        else:
            # for/else：未 break 跑完所有 iter → infinite 模式時觸碰 safety limit
            if infinite:
                log.warning(
                    "workflow_loop_safety_limit_reached",
                    safety_limit=safety_limit,
                    **self._audit_fields(context),
                )
                yield {"event": "loop_safety_limit", "data": json.dumps({"limit": safety_limit})}

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
        from staffkm_core.utils.net import UnsafeURLError, safe_request
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await safe_request(client, method, url, headers=headers, json=body)
            except UnsafeURLError as exc:
                log.warning("http_node_blocked_ssrf", url=url[:200], error=str(exc), **self._audit_fields(context))
                return {"error": f"URL 被 SSRF 防護擋下：{exc}", "blocked": True}
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
        """推播通知（v5.10.9 真實發送）：
          - email：走 SMTP（settings.SMTP_*；未配置則 sent=False）
          - slack：POST 到 incoming webhook（SSRF guard 保護 URL）
          - in_app：無外部通道，寫入 context 供前端/後續節點取用

        config: { channel, target_var | to, subject, template, webhook_url }
        """
        channel = config.get("channel", "in_app")
        target = context.get(config.get("target_var", "")) if config.get("target_var") else None
        message = self._render_template(config.get("template", ""), context)
        sent = False
        detail = ""
        try:
            if channel == "email":
                from app.core.email import send_email
                to = (str(target) if target else self._render_template(config.get("to", ""), context)).strip()
                if "@" in to:
                    sent = await send_email(
                        to=to,
                        subject=self._render_template(config.get("subject", "staffKM 通知"), context),
                        body=message,
                    )
                    detail = "SMTP ok" if sent else "SMTP 未配置或寄送失敗"
                else:
                    detail = "email channel 缺有效收件者"
            elif channel == "slack":
                from staffkm_core.utils.net import UnsafeURLError, safe_request
                webhook = (self._render_template(config.get("webhook_url", ""), context) or str(target or "")).strip()
                if webhook:
                    try:
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            resp = await safe_request(client, "POST", webhook, json={"text": message})
                        sent = resp.status_code < 400
                        detail = f"HTTP {resp.status_code}"
                    except UnsafeURLError as e:
                        detail = f"webhook URL 被 SSRF 防護擋下：{e}"
                else:
                    detail = "slack channel 缺 webhook_url"
            else:  # in_app — 無外部通道，視為已記錄
                sent = True
                detail = "in_app recorded"
        except Exception as e:  # noqa: BLE001
            detail = str(e)[:200]
        log.info(
            "notify_dispatch",
            channel=channel, target=str(target)[:64], sent=sent, detail=detail[:120],
            **self._audit_fields(context),
        )
        context["notify_sent"] = {
            "channel": channel, "target": target, "message": message,
            "sent": sent, "detail": detail,
        }

    async def _exec_email(self, config: dict, context: dict) -> None:
        """Email 寄送節點（v5.10.9 真實 SMTP 發送）。

        config: { to | to_var, subject_template, body_template, html, output_variable }
        收件者：config.to（模板）優先，否則 context[to_var]（預設 recipient_email）。
        SMTP 未配置（settings.SMTP_HOST 空）→ send_email log skip 回 False，sent=False（不視為錯誤）。
        """
        from app.core.email import send_email

        to_tpl = config.get("to")
        to = (
            self._render_template(to_tpl, context) if to_tpl
            else str(context.get(config.get("to_var", "recipient_email"), ""))
        ).strip()
        subject = self._render_template(config.get("subject_template", ""), context)
        body = self._render_template(config.get("body_template", ""), context)

        sent = False
        if "@" in to:
            sent = await send_email(
                to=to, subject=subject, body=body, html=bool(config.get("html", False)),
            )
        else:
            log.warning("email_node_invalid_recipient", to=to[:64], **self._audit_fields(context))

        out_var = config.get("output_variable", "email_drafted")  # 維持舊 key 預設（向後相容）
        context[out_var] = {"to": to, "subject": subject, "body": body, "sent": sent}
        log.info(
            "email_node", to=to[:128], subject=subject[:128], sent=sent,
            **self._audit_fields(context),
        )

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
        expression 是 {{var}} 模板（沿用 _render_template），不執行 eval。

        v2.9：新增 output_type='dict' — 用 keys + values（變數名 list）zip 成 dict 直接寫 output_var；
        預設 output_type='list' 走既有 expression 模板邏輯保 backward compat。
        """
        input_var = config.get("input_variable", "input")
        output_var = config.get("output_variable", "transformed")
        output_type = config.get("output_type", "list")  # MaxKB v2.9: "list" | "dict"

        if output_type == "dict":
            keys = config.get("keys", []) or []
            value_vars = config.get("values", []) or []
            result: dict = {}
            for k, v in zip(keys, value_vars):
                if k:
                    result[str(k)] = context.get(v) if isinstance(v, str) else v
            context[output_var] = result
            return

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
        - 其他 → 用 \\n 串接字串化值

        v2.9：當 output_type='dict' 時走 keys + source_variables zip 模式：
        產出 {keys[i]: context[source_variables[i]]}，覆寫上述 auto 邏輯。
        預設 'list' 保 backward compat。
        """
        sources: list[str] = config.get("source_variables", []) or []
        output_var = config.get("output_variable", "merged")
        output_type = config.get("output_type", "list")

        if output_type == "dict":
            keys = config.get("keys", []) or []
            result: dict = {}
            for k, src in zip(keys, sources):
                if k:
                    result[str(k)] = context.get(src)
            context[output_var] = result
            return

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

    # ── M2 收尾：sandbox 隔離下的 shell 節點 ──────────────────────────────
    async def _exec_shell(self, config: dict, context: dict):
        """執行 user-supplied shell 指令（必須在 workflow_manager='sandbox' 下）。

        config 欄位：
          - argv:        list[str]      必填，wzhell=False，argv[0] 為可執行檔
          - stdin:       str            optional，模板支援 {{var}}
          - timeout_sec: int            預設 10
          - mem_mb:      int            預設 128
          - cpu_secs:    int            預設 5
          - output_variable: str        預設 'shell_output'，回傳 dict(stdout/stderr/exit_code/...)

        強制檢查：
        - workflow_manager 必須是 'sandbox'，否則直接拒絕（避免被當逃逸通道）
        - argv 必須是 list[str] 且 argv[0] 為絕對路徑
        """
        from app.core.sandbox import run_sandboxed

        if self.workflow_manager != "sandbox":
            yield {"event": "shell_blocked", "data": json.dumps({
                "reason": "shell 節點只允許在 workflow_manager='sandbox' 下執行",
            })}
            return

        argv = config.get("argv") or []
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
            yield {"event": "shell_blocked", "data": json.dumps({"reason": "argv 必須是 list[str]"})}
            return
        if not argv[0].startswith("/"):
            yield {"event": "shell_blocked", "data": json.dumps({
                "reason": "argv[0] 必須是絕對路徑（防止 PATH 注入）",
            })}
            return

        stdin_tpl = config.get("stdin")
        stdin = self._render_template(stdin_tpl, context) if stdin_tpl else None

        yield {"event": "shell_exec", "data": json.dumps({
            "argv": argv,
            "timeout_sec": int(config.get("timeout_sec", 10)),
        })}

        res = await run_sandboxed(
            argv,
            stdin=stdin,
            timeout_sec=int(config.get("timeout_sec", 10)),
            mem_mb=int(config.get("mem_mb", 128)),
            cpu_secs=int(config.get("cpu_secs", 5)),
        )

        out_var = config.get("output_variable", "shell_output")
        context[out_var] = {
            "stdout":     res.stdout,
            "stderr":     res.stderr,
            "exit_code":  res.exit_code,
            "timed_out":  res.timed_out,
            "elapsed_ms": res.elapsed_ms,
        }
        yield {"event": "shell_done", "data": json.dumps({
            "exit_code": res.exit_code,
            "timed_out": res.timed_out,
            "elapsed_ms": res.elapsed_ms,
        })}

    # ── v5.10.8：code 節點 — 跑使用者 def run(**kwargs)（對標 MaxKB 函數庫）──
    async def _exec_code_node(self, config: dict, context: dict):
        """在 sandbox 執行使用者 Python `def run(**kwargs) -> dict`，結果寫 output_variable。

        config:
          code:            Python def run(**kwargs) -> dict 原碼（必填）
          inputs:          [{name, value_expression}] — 從 context 渲染後當 kwargs（選填）
          output_variable: 結果寫入的 context key（預設 'code_result'）
          timeout_sec / mem_mb / cpu_secs: sandbox 上限（選填）

        隔離靠 run_python_code（rlimit + timeout + 清空環境 + -I）；
        與 custom tool 共用同一 sandbox helper（DRY）。
        """
        from app.core.sandbox import run_python_code

        out_var = config.get("output_variable", "code_result")
        code = config.get("code") or ""
        if "def run" not in code:
            context[out_var] = {"error": "code 缺少 def run(**kwargs)"}
            yield {"event": "code_error", "data": json.dumps({"error": "code 缺少 def run(**kwargs)"}, ensure_ascii=False)}
            return

        kwargs: dict = {}
        for item in config.get("inputs", []) or []:
            name = item.get("name")
            if name:
                kwargs[name] = self._render_template(item.get("value_expression", ""), context)

        res = await run_python_code(
            code, kwargs,
            timeout_sec=int(config.get("timeout_sec", 15)),
            mem_mb=int(config.get("mem_mb", 256)),
            cpu_secs=int(config.get("cpu_secs", 10)),
        )
        output = res.get("output") if res.get("ok") else {"error": res.get("error")}
        context[out_var] = output
        # 把 dict 結果的頂層 key 攤平進 context，讓 {{field}} 可直接用於後續節點模板
        # （_render_template 只渲染扁平的 str/int/float；dict 本身無法 {{}} 取用）
        if isinstance(output, dict):
            for k, v in output.items():
                if isinstance(k, str) and not k.startswith("_"):
                    context[k] = v
        yield {"event": "code_done", "data": json.dumps({
            "ok": res.get("ok"),
            "elapsed_ms": res.get("elapsed_ms"),
            "error": res.get("error"),
            "output_variable": out_var,
        }, ensure_ascii=False)}

    # ── v2.1 / RFC-013：寫入 workflow KB ───────────────────────────
    async def _exec_kb_writer(self, config: dict, context: dict):
        """寫一段純文字到指定 workflow KB。

        config:
          kb_id:             必填，target KB（必須為 workflow 型）
          content_variable:  必填，從 context 取要寫入的純文字（模板字串）
          title_variable:    可選
          source_variable:   可選
          chunking:          'single'(預設) | 'auto' | 'paragraph'
          upsert_key:        可選，命中時先刪舊 Document
        """
        kb_id = config.get("kb_id")
        if not kb_id:
            yield {"event": "kb_writer_blocked", "data": json.dumps({"reason": "缺 kb_id"})}
            return

        content_tpl = config.get("content_variable") or "{{llm_response}}"
        title_tpl   = config.get("title_variable") or ""
        source_tpl  = config.get("source_variable") or ""
        upsert_tpl  = config.get("upsert_key") or ""

        content = self._render_template(content_tpl, context)
        if not content.strip():
            yield {"event": "kb_writer_skip", "data": json.dumps({"reason": "content 為空"})}
            return

        body: dict[str, Any] = {
            "content":  content,
            "chunking": config.get("chunking", "single"),
        }
        if title_tpl:
            t = self._render_template(title_tpl, context)
            if t: body["title"] = t
        if source_tpl:
            s = self._render_template(source_tpl, context)
            if s: body["source"] = s
        if upsert_tpl:
            uk = self._render_template(upsert_tpl, context)
            if uk: body["upsert_key"] = uk

        url = self._knowledge_url(context, f"documents/{kb_id}/inline-write")
        headers = self._downstream_headers(context)

        yield {"event": "kb_writer_start", "data": json.dumps({
            "kb_id": kb_id, "chunking": body["chunking"],
            "upsert_key": body.get("upsert_key"),
        })}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, headers=headers, json=body)
                if r.status_code >= 400:
                    detail = ""
                    try: detail = r.json().get("detail", "")
                    except Exception: detail = r.text[:200]
                    yield {"event": "kb_writer_error", "data": json.dumps({
                        "status": r.status_code, "detail": detail,
                    })}
                    return
                data = r.json().get("data") or {}
        except Exception as e:
            log.warning("kb_writer_call_failed", error=str(e), **self._audit_fields(context))
            yield {"event": "kb_writer_error", "data": json.dumps({"error": str(e)})}
            return

        out_var = config.get("output_variable", "kb_write_result")
        context[out_var] = data
        yield {"event": "kb_writer_done", "data": json.dumps(data)}

    # ── v3.5 P3：sub_workflow — 呼叫另一個 application 的 workflow ──
    async def _exec_sub_workflow(self, config: dict, context: dict):
        """執行 sub_application 的 workflow，把最後結果塞回外層 context。

        config:
          sub_application_id: UUID (必填)
          input_template:    Jinja string，渲染成 sub workflow 的 user_input
          output_variable:   外層 context 接收 sub 結果的 key（預設 'sub_result'）
        """
        sub_app_id = config.get("sub_application_id")
        if not sub_app_id:
            yield {"event": "error", "data": json.dumps({"error": "sub_workflow: sub_application_id missing"})}
            return
        if not self.workspace_id or not _db._session_factory:
            yield {"event": "error", "data": json.dumps({"error": "sub_workflow needs workspace + DB context"})}
            return

        input_tpl = config.get("input_template", "{{user_input}}")
        try:
            sub_input = self._render_template(input_tpl, context)
        except Exception:
            sub_input = str(input_tpl)

        out_var = config.get("output_variable", "sub_result")

        # 載入 sub workflow
        from app.core.trigger_dispatcher import _load_workflow
        try:
            async with _db._session_factory() as ssession:
                sub_nodes, sub_edges, sub_mgr, _ = await _load_workflow(ssession, sub_app_id, self.workspace_id)
        except Exception as e:
            log.warning("sub_workflow_load_failed", sub=sub_app_id, error=str(e))
            yield {"event": "error", "data": json.dumps({"error": f"sub_workflow load failed: {e}"})}
            return

        # 巢狀 executor（depth+1 防無窮遞迴）
        try:
            sub_exec = WorkflowExecutor(
                nodes=sub_nodes, edges=sub_edges,
                workspace_id=self.workspace_id,
                user_id=self.user_id,
                roles=self.roles,
                workflow_manager=sub_mgr or "simple",
                application_id=sub_app_id,
                run_id=None,         # 不寫 step（避免污染外層 run_id）；sub 的 step 在巢狀 metering 可後續加
                depth=self.depth + 1,
                conversation_id=self.conversation_id,  # v3.8 P1: 繼承外層 conv 歸因
            )
        except RuntimeError as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
            return

        last_data = None
        async for ev in sub_exec.execute(user_input=sub_input, user_id=self.user_id or "sub"):
            name = ev.get("event", "")
            data = ev.get("data", "")
            # 巢狀事件加 sub. prefix 不污染外層 stream
            yield {"event": f"sub.{name}", "data": data}
            if name == "done":
                last_data = data

        context[out_var] = last_data
        yield {"event": "sub_workflow_done", "data": json.dumps({"output_variable": out_var})}
