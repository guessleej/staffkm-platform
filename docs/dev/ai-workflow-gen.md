# AI-generated Workflow（v4.9 I）

讓使用者用自然語言描述需求，由 LLM 產出可直接 import 進 LogicFlow 編輯器的
workflow JSON 草稿。

## 為何要 AI generate

- 30+ node types 的編輯器對新手仍有門檻
- 常見場景（請假審批、文件 RAG、訂單通知…）骨架重複
- v3.x 已穩固的 LLM 抽象 + meter_llm_call → 直接拿來當「workflow 設計助理」

## API

`POST /api/v1/workflow-gen/generate`（gateway proxy → agent service）

Headers:
- `Authorization: Bearer <JWT>`
- `X-Workspace-ID: <ws-uuid>`

Body:
```json
{
  "user_request": "我要做一個請假審批 workflow，超過 3 天要主管核准",
  "model": null
}
```

Response (200):
```json
{
  "data": {
    "workflow": {
      "name": "leave_approval",
      "nodes": [ /* ... */ ],
      "edges": [ /* ... */ ]
    },
    "valid": true,
    "errors": [],
    "raw_response": "...原 LLM 回應..."
  }
}
```

### curl 範例

```bash
curl -X POST https://your-host/api/v1/workflow-gen/generate \
  -H "Authorization: Bearer $JWT" \
  -H "X-Workspace-ID: $WS_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_request":"我要做一個 RAG 問答 workflow"}'
```

## 系統 prompt 結構

`services/agent/app/core/workflow_gen.py` 的 `SYSTEM_PROMPT`：

1. **角色定位**：「staffKM workflow 設計專家」
2. **節點 catalog**：`AVAILABLE_NODES` 動態注入，含 type + 該 type 的 config 欄位
3. **規則**：必須有 start / node_key 唯一 / edges 用 key 連 / 只輸出 JSON
4. **few-shot**：1 個請假審批範例
5. **使用者需求**：尾巴 append `user_request`

LLM 回應後：
- `_extract_json` 容錯 markdown code fence
- `_validate` 檢 nodes/edges/start/type/key/edge endpoints

## 擴充新 node

在 `services/agent/app/core/workflow_gen.py` 的 `AVAILABLE_NODES` 加：

```python
{"type": "your_new_node", "desc": "做什麼. config: { foo, bar }"}
```

`desc` 要包含 type 用途 + config 主要欄位，給 LLM 模仿。

## 前端整合

- `apps/web/src/api/workflowGen.ts`：API client
- `apps/web/src/views/application/AIWorkflowGenModal.vue`：modal 元件
- `WorkflowEditorView.vue` toolbar 的「✨ AI 生成」button

UX 流程：

1. 點 toolbar「✨ AI 生成」開 modal
2. 輸入自然語言需求 → 點「✨ AI 生成」
3. 結果區顯示 valid / errors / nodes & edges count + workflow JSON 預覽
4. 三個動作：
   - **套用到畫布**：emit `apply` 給 parent → `applyAIWorkflow` 用 grid layout
     補位置後走 `apiToLf` + `lf.render`，蓋掉現有畫布內容
   - **下載 JSON**：產生 `<name>.json` 給使用者保存 / 手動 import
   - **複製**：複製到剪貼簿

debug toggle：顯示 raw LLM response。

## Known limitations

- 複雜分支 / loop body 仍需人工調整；驗證只擋明顯結構錯
- 沒做嚴格 JSON Schema（per-node config 沒 deep validate）
- 完全靠 prompt engineering 控品質；換 model 品質會飄
- 套用會蓋掉畫布；目前沒做「merge 進現有 workflow」

## 不做（v4.9 範圍外）

- streaming response
- multi-turn refine（「再加一個 email node」）
- RAG over 自家 docs
- 從 audit_log 學使用者偏好

留作 v5.x backlog。
