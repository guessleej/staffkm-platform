# RFC-002: Workflow Engine v2

| 欄位 | 內容 |
|------|------|
| 編號 | RFC-002 |
| 提案者 | @architect |
| 狀態 | Draft |
| 建立日期 | 2026-05-15 |
| Reviewers | @lead-be @lead-fe @pmp |
| 相關 | RFC-001 (multi-tenant), RFC-005 (sandbox) |

---

## 1. 摘要

重寫 workflow 執行引擎為支援 **DAG + 子流程巢狀 + 三層 scoped context + 35+ 節點型別 + 5 種 manager** 的版本。原 v1 是線性執行 + flat context，無法支援 application_node、loop_continue、variable_aggregation 等進階節點。

## 2. 動機

v1 引擎的限制：
- 沒有 sub-workflow → 無法做 application_node 巢狀
- 變數扁平化 → loop 內外變數覆蓋衝突
- 沒有 trace 表 → debug 困難
- node executor 與 graph executor 耦合 → 加新節點要改核心
- 無暫停 / 等待機制 → form_node、question_node 無法實作

MaxKB 的 workflow_manage.py 已有完整實作參考，但用 Django ORM。我們重新用 FastAPI + asyncio 實作。

## 3. 目標與非目標

**目標**
- [ ] G1：支援 35+ node types（pluggable）
- [ ] G2：sub-workflow 巢狀（application_node 呼叫另一個 workflow）
- [ ] G3：三層 context scope（global / loop / branch）
- [ ] G4：執行可暫停（form / question 節點等使用者輸入）
- [ ] G5：完整 trace 寫 DB（每節點 input/output/elapsed/error）
- [ ] G6：5 種 workflow manager（一般 / loop / tool / knowledge / knowledge+loop）
- [ ] G7：workspace 隔離（呼應 RFC-001）

**非目標**
- N1：不做 distributed workflow（單一 worker，跨機留 v3）
- N2：不做 visual debug step-into（v2 只記 trace，前端後做）

## 4. 提案設計

### 4.1 核心抽象

```python
# core/workflow/types.py
from typing import Protocol, AsyncIterator
from pydantic import BaseModel

class NodeContext(BaseModel):
    workspace_id: UUID
    chat_id:      UUID
    trace_id:     UUID
    variables:    dict          # scoped variables
    parent:       "NodeContext | None"   # 子流程指向父 context

class NodeResult(BaseModel):
    output:       dict          # 寫回 context.variables
    next_node:    str | None    # condition / intent 動態指定
    pause:        bool = False  # form / question 節點

class INode(Protocol):
    type: str
    async def execute(
        self, config: dict, context: NodeContext,
    ) -> AsyncIterator[NodeResult | StreamChunk]: ...
```

### 4.2 三層 Variable Scope

```
global scope
  ├─ user_input, llm_response, knowledge_results …
  │
  ├─ branch scope (condition / intent 分支內)
  │    └─ branch-local 變數
  │
  └─ loop scope (loop 節點內)
       └─ __loop_index__, __item__, body 內 set 的變數
       └─ break 後 loop 變數 destroy，global 保留
```

實作：`NodeContext.variables` 用 ChainMap-like 結構，子作用域 push frame，離開 pop。

### 4.3 Sub-workflow

```python
# application_node 直接呼叫子 workflow
class ApplicationNode:
    async def execute(self, config, ctx):
        sub_app_id = config["application_id"]
        sub_workflow = await load_workflow(sub_app_id, ctx.workspace_id)
        sub_ctx = NodeContext(
            workspace_id = ctx.workspace_id,
            chat_id      = ctx.chat_id,
            trace_id     = uuid4(),     # 新 trace
            variables    = {"user_input": ctx.variables[config["pass_var"]]},
            parent       = ctx,
        )
        executor = WorkflowExecutor(sub_workflow)
        result = await executor.run(sub_ctx)
        yield NodeResult(output={config["output_var"]: result.final_answer})
```

### 4.4 暫停 / 恢復（form / question）

```
form_node 執行 → yield PAUSE event with form schema
   │
   ▼
SSE 推給前端「請填表單」
   │
   ▼
DB 寫入 workflow_pause（state = waiting_input）
   │
   ▼
（時間流逝）
   │
   ▼
用戶提交 → API resume_workflow(pause_id, user_data)
   │
   ▼
從 pause 點繼續執行
```

`workflow_pause` 表 schema：
```sql
CREATE TABLE workflow_pause (
    id              UUID PRIMARY KEY,
    workspace_id    UUID NOT NULL,
    chat_id         UUID NOT NULL,
    trace_id        UUID NOT NULL,
    paused_at_node  VARCHAR(64),
    state_snapshot  JSONB,        -- 完整 context 序列化
    expected_input  JSONB,        -- form schema
    expires_at      TIMESTAMPTZ,
    resumed_at      TIMESTAMPTZ
);
```

### 4.5 Trace 表

```sql
CREATE TABLE workflow_trace (
    id            UUID PRIMARY KEY,
    workspace_id  UUID NOT NULL,
    chat_id       UUID,
    trace_id      UUID NOT NULL,         -- 同一次執行
    parent_trace  UUID,                  -- sub-workflow 指向 caller
    node_key      VARCHAR(64) NOT NULL,
    node_type     VARCHAR(32) NOT NULL,
    input         JSONB,
    output        JSONB,
    elapsed_ms    INTEGER,
    status        VARCHAR(16),           -- success / error / paused
    error         TEXT,
    started_at    TIMESTAMPTZ,
    ended_at      TIMESTAMPTZ
);
CREATE INDEX idx_trace_chat ON workflow_trace(chat_id, started_at);
CREATE INDEX idx_trace_id   ON workflow_trace(trace_id);
```

### 4.6 5 種 Workflow Manager

```
WorkflowManager           ← 一般 application 用（用戶對話）
LoopWorkflowManager       ← 純 loop 流（批次處理）
ToolWorkflowManager       ← 工具型（external API 觸發、無 user）
KnowledgeWorkflowManager  ← 知識庫專用（爬蟲 → 入庫）
KnowledgeLoopWorkflowManager  ← 上面兩個組合（批次入庫）
```

差異主要在：起點節點型別、context 初始化、是否走 SSE、result 持久化策略。

### 4.7 Node Registry

```python
# core/workflow/registry.py
NODE_REGISTRY: dict[str, type[INode]] = {}

def register_node(type_name: str):
    def decorator(cls):
        NODE_REGISTRY[type_name] = cls
        return cls
    return decorator

@register_node("ai_chat")
class AIChatNode: ...

@register_node("knowledge_retrieval")
class KnowledgeRetrievalNode: ...
# ... 35+
```

新增節點不用改核心，只要 `@register_node`。

## 5. 替代方案

| 方案 | 優點 | 缺點 | 為何不選 |
|------|------|------|----------|
| 直接抄 MaxKB 的 Django 實作 | 最快 | 我們是 FastAPI + asyncio，不相容 | 架構不符 |
| 用 LangGraph | 業界活躍 | 抽象層厚、debug 不直覺 | 太框架化、難客製 |
| 用 Temporal | 工業級 | 部署複雜、cluster 必要 | overkill |
| **自寫（本提案）** | 完全可控、貼合需求 | 需自己處理 edge case | **採用** |

## 6. 風險與緩解

| 風險 | 機率 | 衝擊 | 緩解 |
|------|------|------|------|
| DAG 內藏 cycle 造成死鎖 | 中 | 高 | 入庫前用 NetworkX 檢測；執行有 timeout 30s 保險 |
| sub-workflow 無限遞迴 | 中 | 高 | 限制深度 ≤ 5、執行時計數超過直接 abort |
| pause/resume 過期資料堆積 | 中 | 中 | TTL 24h、Celery beat 每日清理 |
| 35 節點品質參差 | 高 | 中 | 每節點必須有 unit test，PR 模板強制 |
| Trace 表暴量 | 高 | 中 | 按月分區（partition）、保留 90 天 |

## 7. 影響範圍

- **DB**：新增 2 表（pause / trace），約 +30% 寫入量
- **API**：新增 `POST /workflow/{id}/resume`、`GET /workflow/trace/{trace_id}`
- **效能**：新引擎用 asyncio.gather 平行執行獨立分支 → 預期快 30%
- **資安**：sub-workflow 跨 workspace 呼叫禁止（middleware 把關）

## 8. 推出計畫

- [ ] **Stage 1**（W4）：核心引擎 + 5 個基本 node（start/llm/answer/condition/knowledge）
- [ ] **Stage 2**（W5-7）：每週 10 個節點批次合併
- [ ] **Stage 3**（W8）：5 個 manager 全上線
- [ ] **Stage 4**（W8）：feature flag 切換 default → v2
- [ ] **Stage 5**（M2 通過後）：v1 引擎 deprecated，3 個月後移除

回滾：feature flag 一秒切回 v1，舊 workflow 仍可執行。

## 9. 量測指標

- 35 個節點全部有 ≥ 1 個 E2E test 通過
- workflow 執行成功率 ≥ 99%（v1 是 95%）
- workflow p95 latency 不退化（不含 LLM 時間）
- pause/resume 成功率 ≥ 99.5%

## 10. 開放問題

- [ ] Q1：sub-workflow 變數傳遞用 implicit pass-through 還是 explicit mapping？@architect to decide
- [ ] Q2：trace 寫 DB 還是 OpenTelemetry？（影響可觀測性整合）@devops
- [ ] Q3：streaming output 在 sub-workflow 內如何 propagate？@lead-be

## 11. 參考資料

- MaxKB `workflow_manage.py`、`step_node/` 模組（docker exec 抽出）
- [LangGraph design notes](https://github.com/langchain-ai/langgraph)
- [Temporal Workflow patterns](https://docs.temporal.io/workflows)
- 內部 RFC-001 (multi-tenant)、RFC-005 (sandbox)
