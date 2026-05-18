/**
 * LogicFlow 自訂節點定義
 * 每個 Workflow 節點型別對應一個 HtmlNode + HtmlNodeModel
 */
import LogicFlow from '@logicflow/core'

// ─── 節點元資料 ────────────────────────────────────────────────────────────────
export interface NodeMeta {
  color: string   // header / border color
  bg: string      // card background
  icon: string    // 2–3 字元節點縮寫（顯示於節點 header）
  label: string   // 中文名稱
  w: number       // 節點寬度
  h: number       // 節點高度
  noInput?: boolean   // Start 節點無 input port
  noOutput?: boolean  // Answer / loop_break 節點無 output port
  dualOutput?: boolean  // Condition 節點有 True + False 兩個 output
}

export const NODE_META: Record<string, NodeMeta> = {
  start:               { color: '#10b981', bg: '#ecfdf5', icon: '▶', label: '開始', w: 160, h: 64, noInput: true },
  llm:                 { color: '#6366f1', bg: '#eef2ff', icon: 'AI',  label: 'AI 對話', w: 190, h: 72 },
  knowledge_retrieval: { color: '#f59e0b', bg: '#fffbeb', icon: 'KB',  label: '知識庫檢索', w: 190, h: 72 },
  condition:           { color: '#8b5cf6', bg: '#f5f3ff', icon: 'IF',  label: '條件判斷', w: 190, h: 84, dualOutput: true },
  variable:            { color: '#06b6d4', bg: '#ecfeff', icon: 'VAR', label: '變數賦值', w: 190, h: 72 },
  http_request:        { color: '#3b82f6', bg: '#eff6ff', icon: 'API', label: 'HTTP 請求', w: 190, h: 72 },
  answer:              { color: '#10b981', bg: '#ecfdf5', icon: 'OUT', label: '回覆訊息', w: 190, h: 72, noOutput: true },
  loop:                { color: '#f97316', bg: '#fff7ed', icon: 'LP',  label: '迴圈', w: 190, h: 72 },
  loop_break:          { color: '#ef4444', bg: '#fef2f2', icon: 'BRK', label: '中斷迴圈', w: 190, h: 64, noOutput: true },
  intent:              { color: '#8b5cf6', bg: '#f5f3ff', icon: 'INT', label: '意圖識別', w: 190, h: 72 },
  parameter_extraction:{ color: '#06b6d4', bg: '#ecfeff', icon: 'EX',  label: '參數萃取', w: 190, h: 72 },
  reranker:            { color: '#f59e0b', bg: '#fffbeb', icon: 'RR',  label: 'Reranker', w: 190, h: 72 },
  speech_to_text:      { color: '#3b82f6', bg: '#eff6ff', icon: 'STT', label: '語音轉文字', w: 190, h: 72 },
  text_to_speech:      { color: '#6366f1', bg: '#eef2ff', icon: 'TTS', label: '文字轉語音', w: 190, h: 72 },
  image_understand:    { color: '#f97316', bg: '#fff7ed', icon: 'IMG', label: '圖像理解', w: 190, h: 72 },
  image_generate:      { color: '#ec4899', bg: '#fdf2f8', icon: 'GEN', label: '圖像生成', w: 190, h: 72 },
  document_extract:    { color: '#64748b', bg: '#f8fafc', icon: 'DOC', label: '文件擷取', w: 190, h: 72 },
  document_split:      { color: '#64748b', bg: '#f8fafc', icon: 'SPL', label: '文件分段', w: 190, h: 72 },
  form:                { color: '#10b981', bg: '#ecfdf5', icon: 'FRM', label: '表單收集', w: 190, h: 72 },
  mcp_tool:            { color: '#6366f1', bg: '#eef2ff', icon: 'MCP', label: 'MCP 工具', w: 190, h: 72 },

  // ── M2 新增節點（scaffold；executor 細部行為由後續 PR 補）─────────
  wait:                { color: '#94a3b8', bg: '#f1f5f9', icon: 'WAIT', label: '等待', w: 160, h: 64 },
  switch:              { color: '#8b5cf6', bg: '#f5f3ff', icon: 'SW',  label: '多分支', w: 190, h: 84, dualOutput: true },
  map:                 { color: '#f59e0b', bg: '#fffbeb', icon: 'MAP', label: '逐項處理', w: 190, h: 72 },
  reduce:              { color: '#ec4899', bg: '#fdf2f8', icon: 'RED', label: '聚合運算', w: 190, h: 72 },
  webhook:             { color: '#3b82f6', bg: '#eff6ff', icon: 'HOOK', label: 'Webhook 觸發', w: 190, h: 72, noInput: true },
  notify:              { color: '#10b981', bg: '#ecfdf5', icon: 'NOT', label: '推播通知', w: 190, h: 72 },
  email:               { color: '#0ea5e9', bg: '#f0f9ff', icon: 'EML', label: '寄送郵件', w: 190, h: 72 },
  schedule:            { color: '#a855f7', bg: '#faf5ff', icon: 'CRON', label: '排程觸發', w: 190, h: 72, noInput: true },
  transform:           { color: '#06b6d4', bg: '#ecfeff', icon: 'TRF', label: '資料轉換', w: 190, h: 72 },
  merge:               { color: '#64748b', bg: '#f8fafc', icon: 'MRG', label: '合併資料流', w: 190, h: 72 },

  // ── v2.1：寫入 workflow KB（RFC-013）──────────────────────────────
  kb_writer:           { color: '#0d9488', bg: '#f0fdfa', icon: 'KW', label: '寫入知識庫', w: 200, h: 72 },

  // ── v3.5 P2：human approval ────────────────────────────────────────
  human_approval:      { color: '#a855f7', bg: '#faf5ff', icon: '人', label: '人工核可', w: 190, h: 72 },
}

// ─── 預設 config ───────────────────────────────────────────────────────────────
export function getDefaultConfig(nodeType: string): Record<string, any> {
  const defaults: Record<string, Record<string, any>> = {
    start:               { user_input_var: 'user_input', system_prompt: '' },
    llm:                 { model: 'gemma4:e4b', temperature: 0.7, max_tokens: 2048, system_prompt: '', prompt_template: '{{user_input}}', stream: true },
    knowledge_retrieval: { kb_ids: [], top_k: 5, similarity_threshold: 0.5, vector_weight: 0.7, search_mode: 'hybrid', output_variable: 'knowledge_results' },
    condition:           { conditions: [{ variable: '', operator: 'contains', value: '' }], logic: 'AND' },
    variable:            { assignments: [{ variable: '', value: '' }] },
    http_request:        { method: 'GET', url: '', headers: {}, body_template: '', output_variable: 'http_response', timeout: 30 },
    answer:              { message_template: '{{llm_response}}', stream: true },
    loop:                { loop_type: 'list', list_variable: '', item_variable: 'item', count: 5, max_iterations: 20, body_nodes: [] },
    loop_break:          {},
    intent:              { method: 'llm', intents: [{ label: '意圖一', keywords: [], next_node_key: '' }], default_next_node_key: '' },
    parameter_extraction:{ method: 'llm', parameters: [{ name: 'param', description: '', type: 'string', required: true }], output_variable: 'extracted_params' },
    reranker:            { provider: 'cohere', top_n: 5, threshold: 0.0, input_variable: 'knowledge_results', output_variable: 'knowledge_results' },
    speech_to_text:      { provider: 'openai', model: 'whisper-1', input_variable: 'audio_input', input_type: 'url', output_variable: 'transcription' },
    text_to_speech:      { provider: 'openai', model: 'tts-1', voice: 'alloy', input_variable: 'llm_response', output_variable: 'audio_output', speed: 1.0 },
    image_understand:    { provider: 'openai', input_variable: 'image_url', input_type: 'url', output_variable: 'image_description', prompt: '請詳細描述這張圖片。' },
    image_generate:      { provider: 'openai', model: 'dall-e-3', prompt_template: '{{user_input}}', size: '1024x1024', quality: 'standard', style: 'vivid', output_variable: 'generated_image_url', output_type: 'url' },
    document_extract:    { input_variable: 'document_url', input_type: 'url', output_variable: 'document_text' },
    document_split:      { input_variable: 'document_text', strategy: 'fixed', chunk_size: 500, chunk_overlap: 50, output_variable: 'chunks' },
    form:                { fields: [{ name: 'user_name', label: '姓名', type: 'text', required: true, default: '', options: [] }] },
    mcp_tool:            { server_url: '', tool_name: '', tool_params_template: '{"query": "{{user_input}}"}', output_variable: 'mcp_result', timeout: 30 },

    // ── M2 新節點預設 config ───────────────────────────────────────
    wait:                { seconds: 5 },
    switch:              { variable: 'user_input', cases: [{ match: '', next_node_key: '' }], default_next_node_key: '' },
    map:                 { list_variable: 'items', item_variable: 'item', body_nodes: [], output_variable: 'mapped' },
    reduce:              { list_variable: 'items', op: 'sum', output_variable: 'total' },
    webhook:             { path: '/webhook/' + Math.random().toString(36).slice(2, 8), secret: '', output_variable: 'webhook_payload' },
    notify:              { channel: 'in_app', template: '{{user_input}}', target_var: '' },
    email:               { to_var: 'recipient_email', subject_template: '', body_template: '' },
    schedule:            { cron: '0 9 * * 1-5', timezone: 'Asia/Taipei' },
    transform:           { input_variable: 'input', expression: '{{input}}', output_variable: 'transformed' },
    merge:               { source_variables: ['a', 'b'], output_variable: 'merged' },

    // ── v2.1：kb_writer（RFC-013）────────────────────────────────
    kb_writer:           {
      kb_id: '',
      content_variable: '{{llm_response}}',
      title_variable: '',
      source_variable: '',
      chunking: 'single',
      upsert_key: '',
      output_variable: 'kb_write_result',
    },

    // ── v3.5 P2：human_approval ──────────────────────────────────
    human_approval:      { approver_role: 'admin', payload_template: '{{user_input}}' },
  }
  return defaults[nodeType] ?? {}
}

// ─── 節點分組（用於左側 Palette）─────────────────────────────────────────────
export const PALETTE_GROUPS = [
  {
    label: '基礎',
    items: ['start', 'llm', 'knowledge_retrieval', 'answer', 'variable'] as const,
  },
  {
    label: '流程控制',
    items: ['condition', 'loop', 'loop_break', 'intent'] as const,
  },
  {
    label: 'AI 處理',
    items: ['parameter_extraction', 'reranker', 'image_understand', 'image_generate'] as const,
  },
  {
    label: '多媒體 / 文件',
    items: ['speech_to_text', 'text_to_speech', 'document_extract', 'document_split'] as const,
  },
  {
    label: '整合',
    items: ['http_request', 'form', 'mcp_tool', 'webhook', 'email', 'notify'] as const,
  },
  // ── M2 新增節點 ────────────────────────────────────────────────
  {
    label: '進階流程控制',
    items: ['wait', 'switch', 'map', 'reduce', 'merge', 'transform'] as const,
  },
  {
    label: '觸發',
    items: ['webhook', 'schedule'] as const,
  },
  // ── v2.1 ──────────────────────────────────────────────────────
  {
    label: '知識庫',
    items: ['kb_writer'] as const,
  },
  // ── v3.5 P2 ──────────────────────────────────────────────────
  {
    label: '人工流程',
    items: ['human_approval'] as const,
  },
]

// ─── 節點 HTML 渲染 ────────────────────────────────────────────────────────────
function renderNodeHtml(meta: NodeMeta, label: string, nodeType: string): string {
  const extraBottom = meta.dualOutput
    ? `<div style="display:flex;justify-content:space-between;padding:4px 10px 6px;background:#f9fafb;border-top:1px solid ${meta.color}22;">
         <span style="font-size:10px;color:#059669;font-weight:600;">▼ True</span>
         <span style="font-size:10px;color:#dc2626;font-weight:600;">False ▼</span>
       </div>`
    : ''

  return `
    <div style="
      width:${meta.w}px;
      background:${meta.bg};
      border:2px solid ${meta.color};
      border-radius:10px;
      overflow:hidden;
      box-shadow:0 2px 8px rgba(0,0,0,0.08);
      font-family:ui-sans-serif,system-ui,sans-serif;
      user-select:none;
    ">
      <div style="background:${meta.color};padding:7px 10px;display:flex;align-items:center;gap:7px;">
        <span style="font-size:14px;line-height:1;">${meta.icon}</span>
        <span style="color:white;font-size:11px;font-weight:700;letter-spacing:0.3px;white-space:nowrap;">${meta.label}</span>
      </div>
      <div style="padding:7px 10px;min-height:20px;">
        <div style="font-size:12px;color:#374151;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:${meta.w - 20}px;">
          ${label || '<span style="color:#9ca3af;font-style:italic;">未命名</span>'}
        </div>
      </div>
      ${extraBottom}
    </div>`
}

// ─── LogicFlow 節點工廠 ────────────────────────────────────────────────────────
function createWorkflowNodeClass(nodeType: string) {
  const meta = NODE_META[nodeType]
  if (!meta) throw new Error(`Unknown node type: ${nodeType}`)

  // @ts-ignore — LogicFlow 1.x class-based API
  class WorkflowNodeView extends (LogicFlow as any).HtmlNode {
    setHtml(rootEl: HTMLElement) {
      const props = (this as any).props.model.properties || {}
      rootEl.innerHTML = renderNodeHtml(meta, props.label || '', nodeType)
    }
  }

  // @ts-ignore
  class WorkflowNodeModel extends (LogicFlow as any).HtmlNodeModel {
    initNodeData(data: any) {
      super.initNodeData(data)
      this.width = meta.w
      this.height = meta.h
      if (!this.properties) this.properties = {}
      if (!this.properties.node_key) {
        this.properties.node_key = `${nodeType}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
      }
      if (!this.properties.config) {
        this.properties.config = getDefaultConfig(nodeType)
      }
    }

    getDefaultAnchor() {
      const { x, y, width, height, id } = this as any
      const anchors: any[] = []

      // Input port (top centre) — Start 節點無 input
      if (!meta.noInput) {
        anchors.push({ x, y: y - height / 2, type: 'input', id: `${id}_i` })
      }

      // Output port(s)
      if (meta.dualOutput) {
        anchors.push({ x: x - width / 4, y: y + height / 2, type: 'output', id: `${id}_true`,  name: 'true'  })
        anchors.push({ x: x + width / 4, y: y + height / 2, type: 'output', id: `${id}_false`, name: 'false' })
      } else if (!meta.noOutput) {
        anchors.push({ x, y: y + height / 2, type: 'output', id: `${id}_o` })
      }

      return anchors
    }

    // 隱藏 LogicFlow 預設的文字節點（我們自己在 HTML 裡顯示）
    getTextStyle() {
      return { ...super.getTextStyle(), fontSize: 0, color: 'transparent' }
    }
  }

  return { type: nodeType, view: WorkflowNodeView, model: WorkflowNodeModel }
}

// ─── 批次註冊所有節點型別 ──────────────────────────────────────────────────────
export function registerWorkflowNodes(lf: LogicFlow) {
  for (const nodeType of Object.keys(NODE_META)) {
    const { type, view, model } = createWorkflowNodeClass(nodeType)
    lf.register({ type, view, model })
  }
}
