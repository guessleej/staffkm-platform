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


class WorkflowExecutor:
    def __init__(
        self,
        nodes: list[dict],
        edges: list[dict],
        app_config: dict = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        roles: list[str] | None = None,
    ):
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
                    true_key = config.get("true_branch")
                    false_key = config.get("false_branch")
                    next_key = true_key if branch else false_key

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

            except Exception as e:
                log.error("workflow_node_failed", node_key=current_key, type=node_type, error=str(e))
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
                next_key = non_condition[0] if non_condition else None

            current_key = next_key

        yield {"event": "citations", "data": json.dumps(context.get("knowledge_results", []))}
        yield {"event": "done", "data": "[DONE]"}

    def _render_template(self, template: str, context: dict) -> str:
        """簡單的 {{variable}} 替換"""
        result = template
        for key, value in context.items():
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

        llm, model = self._build_llm_client(config)
        full_response = ""
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
            log.error("mcp_tool_failed", tool=tool_name, error=str(e))
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
            log.error("image_understand_failed", error=str(e))
            yield f"\n\n⚠️ 圖像分析失敗：{e}"
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
            log.error("image_generate_failed", error=str(e))

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
            log.warning("stt_failed", error=str(e))
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
            log.warning("tts_failed", error=str(e))

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
            log.warning("workflow_reranker_failed", error=str(e), fallback="truncate")
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
                log.warning("parameter_extraction_llm_failed", error=str(e))
                extracted = {p["name"]: str(p.get("default", "")) for p in parameters if p.get("name")}

        # write each extracted value into context
        for name, value in extracted.items():
            context[name] = str(value) if value is not None else ""

        # optionally persist the full JSON under a single variable
        output_var = config.get("output_variable", "")
        if output_var:
            context[output_var] = json.dumps(extracted, ensure_ascii=False)

        return extracted

    async def _exec_intent(self, config: dict, context: dict) -> tuple[str, str | None]:
        """意圖識別：keyword 模式做字串比對，llm 模式請 LLM 回傳意圖編號。"""
        method = config.get("method", "keyword")
        intents: list[dict] = config.get("intents", [])
        text = str(context.get(config.get("variable", "user_input"), ""))
        default_key: str | None = config.get("default_next_node_key") or None

        if method == "keyword":
            for intent in intents:
                for kw in intent.get("keywords", []):
                    if kw and kw in text:
                        return intent.get("label", ""), intent.get("next_node_key") or None
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
                return matched.get("label", ""), matched.get("next_node_key") or None
        except Exception as e:
            log.warning("intent_llm_failed", error=str(e))
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
                    log.error("loop_body_failed", node_key=bkey, error=str(e))
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
