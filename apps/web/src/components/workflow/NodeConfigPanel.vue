<template>
  <div class="flex flex-col h-full">
    <!-- Panel header -->
    <div class="px-4 py-3 border-b border-neutral-200 flex items-center justify-between flex-shrink-0 bg-surface-raised">
      <div class="flex items-center gap-2 min-w-0">
        <span class="text-base flex-shrink-0">{{ meta?.icon }}</span>
        <div class="min-w-0">
          <div class="text-sm font-semibold text-fg truncate">{{ meta?.label }}</div>
          <div class="text-[11px] text-fg-tertiary font-mono">{{ node.node_key }}</div>
        </div>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        <button @click="$emit('delete')" title="刪除節點"
                class="p-1.5 rounded-lg text-fg-tertiary hover:text-rose-500 hover:bg-rose-50 transition">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
          </svg>
        </button>
        <button @click="$emit('close')" title="關閉"
                class="p-1.5 rounded-lg text-fg-tertiary hover:text-fg-secondary hover:bg-neutral-100 transition">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- v2.9：啟用 / 停用 toggle -->
    <div class="px-4 py-2.5 border-b border-neutral-100 bg-surface-raised flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-2">
        <SIcon :name="node.disabled ? 'ban' : 'power'" :size="14"
               :class="node.disabled ? 'text-neutral-400' : 'text-emerald-600'" />
        <span class="text-xs font-medium" :class="node.disabled ? 'text-fg-tertiary' : 'text-fg-secondary'">
          {{ node.disabled ? '已停用（執行時略過）' : '啟用中' }}
        </span>
      </div>
      <button @click="node.disabled = !node.disabled"
              :aria-label="node.disabled ? '啟用此節點' : '停用此節點'"
              :title="node.disabled ? '啟用此節點' : '停用此節點（執行時略過）'"
              class="relative inline-flex h-5 w-9 items-center rounded-full transition focus:outline-none focus:ring-2 focus:ring-indigo-300"
              :class="node.disabled ? 'bg-neutral-300' : 'bg-emerald-500'">
        <span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition"
              :class="node.disabled ? 'translate-x-0.5' : 'translate-x-[18px]'"></span>
      </button>
    </div>

    <!-- Scrollable form body -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4"
         :class="node.disabled ? 'opacity-60' : ''">
      <!-- 共用：節點標籤 -->
      <div>
        <label class="form-label">節點名稱</label>
        <input v-model="node.label" class="form-input" placeholder="（可選）自訂名稱"/>
      </div>

      <!-- ── Start ── -->
      <template v-if="node.node_type === 'start'">
        <div>
          <label class="form-label">使用者輸入變數名</label>
          <input v-model="node.config.user_input_var" class="form-input font-mono text-xs" placeholder="user_input"/>
        </div>
        <div>
          <label class="form-label">System Prompt（全域）</label>
          <textarea v-model="node.config.system_prompt" rows="4" class="form-input resize-none"
                    placeholder="你是一個智能助理…"/>
        </div>
      </template>

      <!-- ── LLM ── -->
      <template v-if="node.node_type === 'llm'">
        <div>
          <label class="form-label">Prompt Template
            <span class="text-fg-tertiary font-normal ml-1">可用 <code v-pre class="bg-neutral-100 px-1 rounded">{{user_input}}</code></span>
          </label>
          <textarea v-model="node.config.prompt_template" rows="5" class="form-input resize-none"
                    placeholder="根據以下知識回答：&#10;{{knowledge_results}}&#10;&#10;問題：{{user_input}}"/>
        </div>
        <div>
          <label class="form-label">System Prompt</label>
          <textarea v-model="node.config.system_prompt" rows="2" class="form-input resize-none font-mono text-xs"
                    placeholder="你是一個企業知識助理。"/>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">Model
              <span class="text-emerald-600 font-normal ml-1">[系統鎖定]</span>
            </label>
            <div class="flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-xl">
              <span class="px-1.5 py-0.5 rounded bg-emerald-200 text-emerald-800 text-[10px] font-semibold">本地</span>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-mono text-emerald-900 font-semibold">gemma4:e4b</div>
                <div class="text-[11px] text-emerald-700">Google Gemma 4 · 多模態 · 128K context · 內網執行</div>
              </div>
            </div>
            <!-- 確保 v-model 仍綁定（即便不顯示 select） -->
            <input type="hidden" :value="node.config.model = 'gemma4:e4b'" />
            <p class="text-[11px] text-fg-tertiary mt-1">依 RFC-005 地端優先策略，本系統僅支援單一 LLM 模型，避免模型混用造成回應品質與權限稽核漂移。</p>
          </div>
          <div>
            <label class="form-label">Temperature</label>
            <input v-model.number="node.config.temperature" type="number" min="0" max="2" step="0.1" class="form-input"/>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">Max Tokens</label>
            <input v-model.number="node.config.max_tokens" type="number" min="64" max="8192" class="form-input"/>
          </div>
          <div class="flex items-end pb-0.5">
            <label class="flex items-center gap-2 text-sm text-fg-secondary cursor-pointer">
              <input type="checkbox" v-model="node.config.stream" class="rounded"/>
              串流輸出
            </label>
          </div>
        </div>
        <!-- v2.8/v2.9：思考過程 toggle（reasoning models）-->
        <div class="flex items-start gap-2 p-2.5 rounded-xl border border-neutral-200 bg-neutral-50">
          <input id="llm_thinking" type="checkbox" v-model="node.config.thinking_process" class="rounded mt-0.5"/>
          <label for="llm_thinking" class="flex-1 cursor-pointer">
            <div class="text-sm font-medium text-fg-secondary">顯示思考過程</div>
            <div class="text-[11px] text-fg-tertiary mt-0.5">開啟後 LLM 會輸出推理步驟（適合 reasoning models）</div>
          </label>
        </div>
        <div>
          <label class="form-label">API Key <span class="text-fg-tertiary font-normal ml-1">（留空使用環境變數）</span></label>
          <input v-model="node.config.api_key" type="password" class="form-input font-mono text-xs" placeholder="sk-…"/>
        </div>
        <div>
          <label class="form-label">Base URL <span class="text-fg-tertiary font-normal ml-1">（自訂 OpenAI 相容端點）</span></label>
          <input v-model="node.config.base_url" class="form-input font-mono text-xs" placeholder="https://api.openai.com/v1"/>
        </div>
      </template>

      <!-- ── Knowledge Retrieval ── -->
      <template v-if="node.node_type === 'knowledge_retrieval'">
        <div>
          <label class="form-label">查詢變數</label>
          <input v-model="node.config.query_variable" class="form-input font-mono text-xs" placeholder="user_input"/>
        </div>
        <div>
          <label class="form-label">知識庫 ID（逗號分隔）</label>
          <input v-model="kbIdsStr" @input="node.config.kb_ids = kbIdsStr.split(',').map(s => s.trim()).filter(Boolean)"
                 class="form-input font-mono text-xs" placeholder="uuid1, uuid2…"/>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">Top K</label>
            <input v-model.number="node.config.top_k" type="number" min="1" max="20" class="form-input"/>
          </div>
          <div>
            <label class="form-label">相似度閾值</label>
            <input v-model.number="node.config.similarity_threshold" type="number" min="0" max="1" step="0.05" class="form-input"/>
          </div>
        </div>
        <div>
          <label class="form-label">搜尋模式</label>
          <select v-model="node.config.search_mode" class="form-input">
            <option value="hybrid">Hybrid（向量 + FTS，RRF 合併）</option>
            <option value="vector">純向量</option>
            <option value="fts">純全文搜尋</option>
          </select>
        </div>
        <div>
          <label class="form-label">輸出變數</label>
          <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="knowledge_results"/>
        </div>
      </template>

      <!-- ── Condition ── -->
      <template v-if="node.node_type === 'condition'">
        <div class="bg-purple-50 border border-purple-100 rounded-xl p-3 text-xs text-purple-700">
          在畫布上從 <strong>True</strong>（左下）或 <strong>False</strong>（右下）連接埠拉線到目標節點。
        </div>
        <div>
          <label class="form-label">條件邏輯</label>
          <select v-model="node.config.logic" class="form-input">
            <option value="AND">AND（全部成立）</option>
            <option value="OR">OR（任一成立）</option>
          </select>
        </div>
        <div>
          <label class="form-label">條件列表</label>
          <div class="space-y-2">
            <div v-for="(cond, ci) in (node.config.conditions || [])" :key="ci"
                 class="flex items-center gap-1.5">
              <input v-model="cond.variable" class="form-input flex-1 font-mono text-xs" placeholder="變數名"/>
              <select v-model="cond.operator" class="text-xs border border-neutral-200 rounded-lg px-2 py-1.5 outline-none focus:border-indigo-400 flex-shrink-0">
                <option value="contains">包含</option>
                <option value="not_contains">不包含</option>
                <option value="equals">等於</option>
                <option value="not_equals">不等於</option>
                <option value="gt">大於</option>
                <option value="lt">小於</option>
                <option value="is_empty">為空</option>
                <option value="not_empty">不為空</option>
              </select>
              <input v-model="cond.value" class="form-input flex-1 font-mono text-xs" placeholder="值"/>
              <button @click="node.config.conditions.splice(ci, 1)"
                      class="text-fg-tertiary hover:text-rose-500 transition text-lg leading-none flex-shrink-0">×</button>
            </div>
          </div>
          <button @click="(node.config.conditions = node.config.conditions || []).push({ variable: '', operator: 'contains', value: '' })"
                  class="mt-2 text-xs text-indigo-600 hover:text-indigo-700 font-medium">+ 加入條件</button>
        </div>
      </template>

      <!-- ── Variable ── -->
      <template v-if="node.node_type === 'variable'">
        <div>
          <label class="form-label">變數賦值</label>
          <div class="space-y-2">
            <div v-for="(asgn, ai) in (node.config.assignments || [])" :key="ai"
                 class="flex items-center gap-1.5">
              <input v-model="asgn.variable" class="form-input flex-1 font-mono text-xs" placeholder="var_name"/>
              <span class="text-fg-tertiary text-xs flex-shrink-0">=</span>
              <input v-model="asgn.value" class="form-input flex-1 font-mono text-xs" placeholder="{{user_input}}"/>
              <button @click="node.config.assignments.splice(ai, 1)"
                      class="text-fg-tertiary hover:text-rose-500 transition text-lg leading-none flex-shrink-0">×</button>
            </div>
          </div>
          <button @click="(node.config.assignments = node.config.assignments || []).push({ variable: '', value: '' })"
                  class="mt-2 text-xs text-indigo-600 hover:text-indigo-700 font-medium">+ 加入變數</button>
        </div>
      </template>

      <!-- ── HTTP Request ── -->
      <template v-if="node.node_type === 'http_request'">
        <div class="flex gap-2">
          <select v-model="node.config.method" class="text-xs border border-neutral-200 rounded-lg px-2 py-1.5 outline-none focus:border-indigo-400 flex-shrink-0">
            <option>GET</option><option>POST</option><option>PUT</option><option>DELETE</option><option>PATCH</option>
          </select>
          <input v-model="node.config.url" class="form-input flex-1 font-mono text-xs" placeholder="https://api.example.com/{{path}}"/>
        </div>
        <div>
          <label class="form-label">Headers（JSON）</label>
          <textarea :value="JSON.stringify(node.config.headers ?? {}, null, 2)"
                    @change="tryParseJson($event, v => node.config.headers = v)"
                    rows="3" class="form-input resize-none font-mono text-xs" placeholder='{"Authorization": "Bearer {{token}}"}'/>
        </div>
        <div>
          <label class="form-label">Body Template</label>
          <textarea v-model="node.config.body_template" rows="3" class="form-input resize-none font-mono text-xs"
                    placeholder='{"query": "{{user_input}}"}'/>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸出變數</label>
            <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="http_response"/>
          </div>
          <div>
            <label class="form-label">逾時（秒）</label>
            <input v-model.number="node.config.timeout" type="number" min="5" max="300" class="form-input"/>
          </div>
        </div>
      </template>

      <!-- ── Answer ── -->
      <template v-if="node.node_type === 'answer'">
        <div>
          <label class="form-label">回覆模板
            <span class="text-fg-tertiary font-normal ml-1">可用 <code v-pre class="bg-neutral-100 px-1 rounded">{{llm_response}}</code></span>
          </label>
          <textarea v-model="node.config.message_template" rows="5" class="form-input resize-none"
                    placeholder="{{llm_response}}"/>
        </div>
        <div class="flex items-center gap-2">
          <input type="checkbox" v-model="node.config.stream" class="rounded" id="answer_stream"/>
          <label for="answer_stream" class="text-sm text-fg-secondary cursor-pointer">串流輸出</label>
        </div>
      </template>

      <!-- ── Loop ── -->
      <template v-if="node.node_type === 'loop'">
        <div>
          <label class="form-label">迴圈類型</label>
          <select v-model="node.config.loop_type" class="form-input">
            <option value="count">計數（Count）</option>
            <option value="list">清單迭代（List）</option>
            <option value="while">條件迴圈（While）</option>
          </select>
        </div>
        <template v-if="node.config.loop_type === 'count'">
          <div>
            <label class="form-label">迭代次數</label>
            <input v-model.number="node.config.count" type="number" min="1" max="50" class="form-input"/>
          </div>
        </template>
        <template v-if="node.config.loop_type === 'list'">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="form-label">清單變數</label>
              <input v-model="node.config.list_variable" class="form-input font-mono text-xs" placeholder="chunks"/>
            </div>
            <div>
              <label class="form-label">迭代元素變數</label>
              <input v-model="node.config.item_variable" class="form-input font-mono text-xs" placeholder="item"/>
            </div>
          </div>
        </template>
        <template v-if="node.config.loop_type === 'while'">
          <div>
            <label class="form-label">條件變數（Truthy 時繼續）</label>
            <input v-model="node.config.condition_variable" class="form-input font-mono text-xs" placeholder="should_continue"/>
          </div>
        </template>
        <div>
          <label class="form-label">最大迭代次數（上限）</label>
          <input v-model.number="node.config.max_iterations" type="number" min="1" max="50" class="form-input"/>
        </div>
        <div class="bg-orange-50 border border-orange-100 rounded-xl p-3 text-xs text-orange-700">
          迴圈本體的節點直接在 Loop 節點的下方連接，遇到 <strong>⏹ 中斷迴圈</strong> 節點時結束。
        </div>
      </template>

      <!-- ── Intent ── -->
      <template v-if="node.node_type === 'intent'">
        <div>
          <label class="form-label">識別方式</label>
          <select v-model="node.config.method" class="form-input">
            <option value="keyword">關鍵字比對</option>
            <option value="llm">LLM 分類</option>
          </select>
        </div>
        <div>
          <label class="form-label">意圖列表</label>
          <div class="space-y-3">
            <div v-for="(intent, ii) in (node.config.intents || [])" :key="ii"
                 class="border border-neutral-200 rounded-xl p-3 space-y-2">
              <div class="flex items-center gap-2">
                <input v-model="intent.label" class="form-input flex-1 text-xs" placeholder="意圖名稱"/>
                <button @click="node.config.intents.splice(ii, 1)"
                        class="text-fg-tertiary hover:text-rose-500 transition text-lg leading-none">×</button>
              </div>
              <div v-if="node.config.method === 'keyword'">
                <input :value="(intent.keywords || []).join(', ')"
                       @input="intent.keywords = ($event.target as HTMLInputElement).value.split(',').map(s => s.trim()).filter(Boolean)"
                       class="form-input text-xs font-mono" placeholder="關鍵字一, 關鍵字二…"/>
              </div>
            </div>
          </div>
          <button @click="(node.config.intents = node.config.intents || []).push({ label: '', keywords: [], next_node_key: '' })"
                  class="mt-2 text-xs text-indigo-600 hover:text-indigo-700 font-medium">+ 加入意圖</button>
        </div>
      </template>

      <!-- ── Parameter Extraction ── -->
      <template v-if="node.node_type === 'parameter_extraction'">
        <div>
          <label class="form-label">萃取方式</label>
          <select v-model="node.config.method" class="form-input">
            <option value="llm">LLM 結構化輸出</option>
            <option value="regex">正規表達式</option>
          </select>
        </div>
        <div>
          <label class="form-label">參數定義</label>
          <div class="space-y-2">
            <div v-for="(param, pi) in (node.config.parameters || [])" :key="pi"
                 class="border border-neutral-200 rounded-xl p-2 space-y-1.5">
              <div class="flex items-center gap-2">
                <input v-model="param.name" class="form-input flex-1 font-mono text-xs" placeholder="param_name"/>
                <select v-model="param.type" class="text-xs border border-neutral-200 rounded-lg px-2 py-1.5 outline-none flex-shrink-0">
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="array">array</option>
                </select>
                <button @click="node.config.parameters.splice(pi, 1)"
                        class="text-fg-tertiary hover:text-rose-500 transition text-lg leading-none flex-shrink-0">×</button>
              </div>
              <input v-model="param.description" class="form-input text-xs" placeholder="參數說明"/>
              <label class="flex items-center gap-1.5 text-xs text-fg-secondary cursor-pointer">
                <input type="checkbox" v-model="param.required" class="rounded"/> 必填
              </label>
            </div>
          </div>
          <button @click="(node.config.parameters = node.config.parameters || []).push({ name: '', description: '', type: 'string', required: true })"
                  class="mt-2 text-xs text-indigo-600 hover:text-indigo-700 font-medium">+ 加入參數</button>
        </div>
        <div>
          <label class="form-label">輸出變數</label>
          <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="extracted_params"/>
        </div>
      </template>

      <!-- ── Reranker ── -->
      <template v-if="node.node_type === 'reranker'">
        <div>
          <label class="form-label">服務提供者</label>
          <select v-model="node.config.provider" class="form-input">
            <option value="cohere">Cohere Rerank v2</option>
            <option value="http">自訂 HTTP（Cohere API 相容）</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸入變數</label>
            <input v-model="node.config.input_variable" class="form-input font-mono text-xs" placeholder="knowledge_results"/>
          </div>
          <div>
            <label class="form-label">輸出變數</label>
            <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="knowledge_results"/>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">Top N</label>
            <input v-model.number="node.config.top_n" type="number" min="1" max="20" class="form-input"/>
          </div>
          <div>
            <label class="form-label">分數閾值</label>
            <input v-model.number="node.config.threshold" type="number" min="0" max="1" step="0.05" class="form-input"/>
          </div>
        </div>
        <div>
          <label class="form-label">API Key</label>
          <input v-model="node.config.api_key" type="password" class="form-input font-mono text-xs" placeholder="sk-…"/>
        </div>
        <div v-if="node.config.provider === 'http'">
          <label class="form-label">Base URL</label>
          <input v-model="node.config.base_url" class="form-input font-mono text-xs" placeholder="http://reranker:8080"/>
        </div>
      </template>

      <!-- ── Speech to Text ── -->
      <template v-if="node.node_type === 'speech_to_text'">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸入變數</label>
            <input v-model="node.config.input_variable" class="form-input font-mono text-xs" placeholder="audio_input"/>
          </div>
          <div>
            <label class="form-label">輸出變數</label>
            <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="transcription"/>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸入類型</label>
            <select v-model="node.config.input_type" class="form-input">
              <option value="url">URL</option><option value="base64">Base64</option>
            </select>
          </div>
          <div>
            <label class="form-label">Model</label>
            <input v-model="node.config.model" class="form-input font-mono text-xs" placeholder="whisper-1"/>
          </div>
        </div>
        <div>
          <label class="form-label">API Key</label>
          <input v-model="node.config.api_key" type="password" class="form-input font-mono text-xs" placeholder="sk-…"/>
        </div>
      </template>

      <!-- ── Text to Speech ── -->
      <template v-if="node.node_type === 'text_to_speech'">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸入變數</label>
            <input v-model="node.config.input_variable" class="form-input font-mono text-xs" placeholder="llm_response"/>
          </div>
          <div>
            <label class="form-label">輸出變數</label>
            <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="audio_output"/>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">聲音（Voice）</label>
            <select v-model="node.config.voice" class="form-input">
              <option v-for="v in ['alloy','echo','fable','onyx','nova','shimmer']" :key="v" :value="v">{{ v }}</option>
            </select>
          </div>
          <div>
            <label class="form-label">語速（0.25–4）</label>
            <input v-model.number="node.config.speed" type="number" min="0.25" max="4" step="0.25" class="form-input"/>
          </div>
        </div>
      </template>

      <!-- ── Image Understand ── -->
      <template v-if="node.node_type === 'image_understand'">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">圖片來源變數</label>
            <input v-model="node.config.input_variable" class="form-input font-mono text-xs" placeholder="image_url"/>
          </div>
          <div>
            <label class="form-label">輸入類型</label>
            <select v-model="node.config.input_type" class="form-input">
              <option value="url">URL</option><option value="base64">Base64</option>
            </select>
          </div>
        </div>
        <div>
          <label class="form-label">輸出變數</label>
          <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="image_description"/>
        </div>
        <div>
          <label class="form-label">Prompt</label>
          <textarea v-model="node.config.prompt" rows="3" class="form-input resize-none" placeholder="請詳細描述這張圖片的內容。"/>
        </div>
        <!-- v2.8/v2.9：思考過程 toggle -->
        <div class="flex items-start gap-2 p-2.5 rounded-xl border border-neutral-200 bg-neutral-50">
          <input id="iu_thinking" type="checkbox" v-model="node.config.thinking_process" class="rounded mt-0.5"/>
          <label for="iu_thinking" class="flex-1 cursor-pointer">
            <div class="text-sm font-medium text-fg-secondary">顯示思考過程</div>
            <div class="text-[11px] text-fg-tertiary mt-0.5">開啟後模型會輸出推理步驟（適合 reasoning models）</div>
          </label>
        </div>
      </template>

      <!-- ── Image Generate ── -->
      <template v-if="node.node_type === 'image_generate'">
        <div>
          <label class="form-label">Prompt Template</label>
          <textarea v-model="node.config.prompt_template" rows="3" class="form-input resize-none" placeholder="{{user_input}}"/>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">Model</label>
            <!-- v2.7：searchable model dropdown -->
            <SearchableModelSelect v-model="node.config.model" :options="IMAGE_GEN_MODELS" />
          </div>
          <div>
            <label class="form-label">尺寸</label>
            <select v-model="node.config.size" class="form-input">
              <option value="1024x1024">1024×1024</option>
              <option value="1792x1024">1792×1024</option>
              <option value="1024x1792">1024×1792</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸出變數</label>
            <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="generated_image_url"/>
          </div>
          <div>
            <label class="form-label">輸出類型</label>
            <select v-model="node.config.output_type" class="form-input">
              <option value="url">URL</option><option value="base64">Base64</option>
            </select>
          </div>
        </div>
      </template>

      <!-- ── Document Extract ── -->
      <template v-if="node.node_type === 'document_extract'">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸入變數</label>
            <input v-model="node.config.input_variable" class="form-input font-mono text-xs" placeholder="document_url"/>
          </div>
          <div>
            <label class="form-label">輸入類型</label>
            <select v-model="node.config.input_type" class="form-input">
              <option value="url">URL</option><option value="base64">Base64</option>
            </select>
          </div>
        </div>
        <div>
          <label class="form-label">輸出變數</label>
          <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="document_text"/>
        </div>
      </template>

      <!-- ── Document Split ── -->
      <template v-if="node.node_type === 'document_split'">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸入文字變數</label>
            <input v-model="node.config.input_variable" class="form-input font-mono text-xs" placeholder="document_text"/>
          </div>
          <div>
            <label class="form-label">輸出變數（陣列）</label>
            <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="chunks"/>
          </div>
        </div>
        <div>
          <label class="form-label">切分策略</label>
          <select v-model="node.config.strategy" class="form-input">
            <option value="fixed">固定長度</option>
            <option value="paragraph">段落</option>
            <option value="sentence">句子</option>
            <option value="separator">自訂分隔符</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">Chunk 大小</label>
            <input v-model.number="node.config.chunk_size" type="number" min="50" max="8000" class="form-input"/>
          </div>
          <div v-if="node.config.strategy === 'fixed'">
            <label class="form-label">重疊字元</label>
            <input v-model.number="node.config.chunk_overlap" type="number" min="0" max="500" class="form-input"/>
          </div>
        </div>
      </template>

      <!-- ── Form ── -->
      <template v-if="node.node_type === 'form'">
        <div>
          <label class="form-label">表單欄位</label>
          <div class="space-y-3">
            <div v-for="(field, fi) in (node.config.fields || [])" :key="fi"
                 class="border border-neutral-200 rounded-xl p-3 space-y-2">
              <div class="flex items-center gap-2">
                <input v-model="field.name" class="form-input flex-1 font-mono text-xs" placeholder="變數名"/>
                <select v-model="field.type"
                        class="text-xs border border-neutral-200 rounded-lg px-2 py-1.5 outline-none flex-shrink-0">
                  <option value="text">text</option>
                  <option value="textarea">textarea</option>
                  <option value="number">number</option>
                  <option value="select">select</option>
                  <option value="date">date</option>
                </select>
                <button @click="node.config.fields.splice(fi, 1)"
                        class="text-fg-tertiary hover:text-rose-500 transition text-lg leading-none flex-shrink-0">×</button>
              </div>
              <input v-model="field.label" class="form-input text-xs" placeholder="顯示標籤"/>
              <div class="flex items-center gap-3">
                <label class="flex items-center gap-1.5 text-xs cursor-pointer">
                  <input type="checkbox" v-model="field.required" class="rounded"/> 必填
                </label>
                <input v-model="field.default" class="form-input text-xs flex-1" placeholder="預設值"/>
              </div>
              <div v-if="field.type === 'select'">
                <textarea :value="(field.options || []).join('\n')"
                          @input="field.options = ($event.target as HTMLTextAreaElement).value.split('\n').map((s:string) => s.trim()).filter(Boolean)"
                          rows="2" class="form-input resize-none font-mono text-xs" placeholder="選項一&#10;選項二"/>
              </div>
            </div>
          </div>
          <button @click="(node.config.fields = node.config.fields || []).push({ name: '', label: '', type: 'text', required: true, default: '', options: [] })"
                  class="mt-2 text-xs text-indigo-600 hover:text-indigo-700 font-medium">+ 加入欄位</button>
        </div>
      </template>

      <!-- ── MCP Tool ── -->
      <template v-if="node.node_type === 'mcp_tool'">
        <div>
          <label class="form-label">MCP Server URL</label>
          <input v-model="node.config.server_url" class="form-input font-mono text-xs" placeholder="http://mcp-server:3000"/>
        </div>
        <div>
          <label class="form-label">工具名稱</label>
          <input v-model="node.config.tool_name" class="form-input font-mono text-xs" placeholder="search_web"/>
        </div>
        <div>
          <label class="form-label">參數 JSON Template</label>
          <textarea v-model="node.config.tool_params_template" rows="3" class="form-input resize-none font-mono text-xs"
                    placeholder='{"query": "{{user_input}}"}'/>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">輸出變數</label>
            <input v-model="node.config.output_variable" class="form-input font-mono text-xs" placeholder="mcp_result"/>
          </div>
          <div>
            <label class="form-label">逾時（秒）</label>
            <input v-model.number="node.config.timeout" type="number" min="5" max="300" class="form-input"/>
          </div>
        </div>
        <div>
          <label class="form-label">API Key（選填）</label>
          <input v-model="node.config.api_key" type="password" class="form-input font-mono text-xs" placeholder="Bearer token"/>
        </div>
      </template>

      <!-- ── v2.1：寫入知識庫（RFC-013）─────────────────────────────── -->
      <template v-if="node.node_type === 'kb_writer'">
        <div>
          <label class="form-label">目標知識庫</label>
          <!-- v2.7：searchable dropdown + hover tooltip 顯示 KB metadata -->
          <div class="relative" v-click-outside="() => (kbDropdownOpen = false)">
            <button type="button"
                    @click="kbDropdownOpen = !kbDropdownOpen; $nextTick(() => kbSearchInputRef?.focus())"
                    class="form-input font-mono text-xs text-left flex items-center justify-between"
                    :aria-expanded="kbDropdownOpen">
              <span class="truncate" :class="!selectedKbName ? 'text-fg-tertiary' : ''">
                {{ selectedKbName || '請選擇（必須為 workflow KB）' }}
              </span>
              <SIcon name="chevron-down" :size="12" class="text-fg-tertiary flex-shrink-0 ml-1"/>
            </button>
            <div v-if="kbDropdownOpen"
                 class="absolute z-20 top-full left-0 right-0 mt-1 bg-surface-raised border border-neutral-200 rounded-xl shadow-lg max-h-64 overflow-hidden flex flex-col">
              <div class="p-2 border-b border-neutral-100">
                <input ref="kbSearchInputRef" v-model="kbSearch"
                       class="w-full text-xs border border-neutral-200 rounded-lg px-2 py-1.5 focus:outline-none focus:border-indigo-400"
                       placeholder="搜尋知識庫…" aria-label="搜尋知識庫" />
              </div>
              <div class="flex-1 overflow-y-auto py-1">
                <p v-if="!filteredKbs.length" class="text-xs text-fg-tertiary text-center py-3">無符合結果</p>
                <button v-for="kb in filteredKbs" :key="kb.id" type="button"
                        @click="node.config.kb_id = kb.id; kbDropdownOpen = false; kbSearch = ''"
                        @mouseenter="kbHover = kb.id" @mouseleave="kbHover = null"
                        class="relative w-full text-left px-3 py-1.5 text-xs hover:bg-indigo-50 flex items-center justify-between gap-2"
                        :class="node.config.kb_id === kb.id ? 'bg-indigo-50 text-indigo-700' : 'text-fg-secondary'">
                  <span class="truncate" v-html="highlightMatch(kb.name, kbSearch)"></span>
                  <SIcon v-if="node.config.kb_id === kb.id" name="check" :size="12" class="text-indigo-600 flex-shrink-0"/>
                  <!-- hover tooltip: KB metadata -->
                  <div v-if="kbHover === kb.id"
                       class="absolute left-full top-0 ml-2 z-30 w-56 bg-fg text-white text-[11px] rounded-lg shadow-xl p-2.5 pointer-events-none">
                    <div class="font-semibold mb-1">{{ kb.name }}</div>
                    <div class="opacity-80 font-mono text-[10px] break-all">{{ kb.id }}</div>
                    <div class="opacity-80 mt-1">類型：工作流知識庫</div>
                  </div>
                </button>
              </div>
            </div>
          </div>
          <p class="text-[10px] text-neutral-400 mt-1">
            僅顯示已標記為「工作流知識庫」的 KB；可在 /knowledge 該 KB 卡片按閃電鍵轉換。
          </p>
        </div>
        <div>
          <label class="form-label">內容變數 / 模板</label>
          <textarea v-model="node.config.content_variable" rows="2"
                    class="form-input resize-none font-mono text-xs"
                    placeholder="{{llm_response}} 或 {{summary}}" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">段落標題（選填）</label>
            <input v-model="node.config.title_variable" class="form-input font-mono text-xs"
                   placeholder="{{title}}"/>
          </div>
          <div>
            <label class="form-label">來源 URL（選填）</label>
            <input v-model="node.config.source_variable" class="form-input font-mono text-xs"
                   placeholder="{{source_url}}"/>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">切片模式</label>
            <select v-model="node.config.chunking" class="form-input text-xs">
              <option value="single">single（整段一筆）</option>
              <option value="paragraph">paragraph（空行切）</option>
              <option value="auto">auto（按 KB chunk_size）</option>
            </select>
          </div>
          <div>
            <label class="form-label">Upsert Key（去重）</label>
            <input v-model="node.config.upsert_key" class="form-input font-mono text-xs"
                   placeholder="{{ticket_id}} 留空 = 不去重"/>
          </div>
        </div>
        <div>
          <label class="form-label">輸出變數（kb_write_result）</label>
          <input v-model="node.config.output_variable" class="form-input font-mono text-xs"
                 placeholder="kb_write_result"/>
        </div>
      </template>

    </div><!-- /form body -->
  </div>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onBeforeUnmount, onMounted, ref, watch, defineComponent } from 'vue'
import type { Directive } from 'vue'
import { NODE_META } from './lf-nodes'
import { knowledgeApi } from '../../api/knowledge'
import { SIcon } from '@staffkm/ui-kit'

// v2.7：點外面關閉 dropdown
const vClickOutside: Directive<HTMLElement, () => void> = {
  mounted(el, binding) {
    ;(el as any).__cob__ = (ev: MouseEvent) => {
      if (!el.contains(ev.target as Node)) binding.value?.()
    }
    document.addEventListener('mousedown', (el as any).__cob__)
  },
  unmounted(el) {
    document.removeEventListener('mousedown', (el as any).__cob__)
  },
}

// v2.7：泛用 searchable model dropdown
const SearchableModelSelect = defineComponent({
  props: {
    modelValue: { type: String, default: '' },
    options: { type: Array as () => { value: string; label: string; hint?: string }[], required: true },
  },
  emits: ['update:modelValue'],
  setup(p, { emit }) {
    const open = ref(false)
    const q = ref('')
    const inputRef = ref<HTMLInputElement | null>(null)
    const hover = ref<string | null>(null)
    const filtered = computed(() => {
      const k = q.value.trim().toLowerCase()
      if (!k) return p.options
      return p.options.filter((o) => o.value.toLowerCase().includes(k) || o.label.toLowerCase().includes(k))
    })
    const selectedLabel = computed(() => p.options.find((o) => o.value === p.modelValue)?.label || p.modelValue || '請選擇模型')
    function hl(s: string, kw: string) {
      if (!kw.trim()) return s
      const i = s.toLowerCase().indexOf(kw.trim().toLowerCase())
      if (i < 0) return s
      return s.slice(0, i) + '<mark class="bg-yellow-200 text-fg">' + s.slice(i, i + kw.length) + '</mark>' + s.slice(i + kw.length)
    }
    function pick(v: string) {
      emit('update:modelValue', v)
      open.value = false
      q.value = ''
    }
    function toggle() {
      open.value = !open.value
      if (open.value) nextTick(() => inputRef.value?.focus())
    }
    const closeFn = () => (open.value = false)
    return () =>
      h('div', { class: 'relative', directives: undefined }, [
        h(
          'button',
          {
            type: 'button',
            onClick: toggle,
            class: 'w-full text-sm border border-neutral-200 rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-400 text-left flex items-center justify-between',
            'aria-expanded': open.value,
          },
          [
            h('span', { class: 'truncate' }, selectedLabel.value),
            h(SIcon, { name: 'chevron-down', size: 12, class: 'text-fg-tertiary flex-shrink-0 ml-1' }),
          ],
        ),
        open.value &&
          h(
            'div',
            {
              class: 'absolute z-20 top-full left-0 right-0 mt-1 bg-surface-raised border border-neutral-200 rounded-xl shadow-lg max-h-64 overflow-hidden flex flex-col',
            },
            [
              h('div', { class: 'p-2 border-b border-neutral-100' }, [
                h('input', {
                  ref: inputRef,
                  value: q.value,
                  onInput: (e: Event) => (q.value = (e.target as HTMLInputElement).value),
                  class: 'w-full text-xs border border-neutral-200 rounded-lg px-2 py-1.5 focus:outline-none focus:border-indigo-400',
                  placeholder: '搜尋模型…',
                  'aria-label': '搜尋模型',
                }),
              ]),
              h(
                'div',
                { class: 'flex-1 overflow-y-auto py-1' },
                filtered.value.length
                  ? filtered.value.map((opt) =>
                      h(
                        'button',
                        {
                          key: opt.value,
                          type: 'button',
                          onClick: () => pick(opt.value),
                          onMouseenter: () => (hover.value = opt.value),
                          onMouseleave: () => (hover.value = null),
                          class:
                            'relative w-full text-left px-3 py-1.5 text-xs hover:bg-indigo-50 flex items-center justify-between gap-2 ' +
                            (p.modelValue === opt.value ? 'bg-indigo-50 text-indigo-700' : 'text-fg-secondary'),
                        },
                        [
                          h('span', { class: 'truncate', innerHTML: hl(opt.label, q.value) }),
                          p.modelValue === opt.value &&
                            h(SIcon, { name: 'check', size: 12, class: 'text-indigo-600 flex-shrink-0' }),
                          hover.value === opt.value && opt.hint
                            ? h(
                                'div',
                                {
                                  class:
                                    'absolute left-full top-0 ml-2 z-30 w-56 bg-fg text-white text-[11px] rounded-lg shadow-xl p-2.5 pointer-events-none',
                                },
                                opt.hint,
                              )
                            : null,
                        ],
                      ),
                    )
                  : [h('p', { class: 'text-xs text-fg-tertiary text-center py-3' }, '無符合結果')],
              ),
            ],
          ),
        // click-outside via window listener
        h('span', {
          style: 'display:none',
          ref: (el: any) => {
            if (!el) return
            ;(el as any).__close = closeFn
          },
        }),
      ])
  },
})

const IMAGE_GEN_MODELS = [
  { value: 'dall-e-3', label: 'DALL-E 3', hint: 'OpenAI · 高品質 · 支援 HD' },
  { value: 'dall-e-2', label: 'DALL-E 2', hint: 'OpenAI · 較舊版本 · 速度較快' },
]

const props = defineProps<{
  node: {
    id: string
    node_key: string
    node_type: string
    label: string
    config: Record<string, any>
    disabled?: boolean
  }
}>()

// v2.9：確保 disabled 欄位存在（向下相容舊 workflow）
if (props.node.disabled === undefined) {
  ;(props.node as any).disabled = false
}

defineEmits<{
  close: []
  delete: []
}>()

const meta = computed(() => NODE_META[props.node.node_type])

// ── v2.7：kb_writer 的 searchable + hover tooltip dropdown state ─────────
const kbDropdownOpen = ref(false)
const kbSearch = ref('')
const kbSearchInputRef = ref<HTMLInputElement | null>(null)
const kbHover = ref<string | null>(null)
const filteredKbs = computed(() => {
  const k = kbSearch.value.trim().toLowerCase()
  if (!k) return workflowKbs.value
  return workflowKbs.value.filter((kb) => kb.name.toLowerCase().includes(k) || kb.id.toLowerCase().includes(k))
})
const selectedKbName = computed(() => workflowKbs.value.find((kb) => kb.id === props.node.config.kb_id)?.name || '')
function highlightMatch(text: string, kw: string) {
  if (!kw.trim()) return text
  const i = text.toLowerCase().indexOf(kw.trim().toLowerCase())
  if (i < 0) return text
  return text.slice(0, i) + '<mark class="bg-yellow-200 text-fg">' + text.slice(i, i + kw.length) + '</mark>' + text.slice(i + kw.length)
}

// ── v2.1：kb_writer node — 載入 workspace 內所有「workflow KB」供下拉 ──
const workflowKbs = ref<{ id: string; name: string }[]>([])
async function loadWorkflowKbs() {
  try {
    const resp: any = await knowledgeApi.listBases(1, 200)
    const all = (resp?.data?.items ?? resp?.items ?? resp?.data ?? []) as any[]
    // 逐筆查 source_type（API 暫無 filter；只挑出 workflow）
    const out: { id: string; name: string }[] = []
    for (const kb of all) {
      try {
        const info = await knowledgeApi.getKbSourceInfo(kb.id)
        if (info?.source_type === 'workflow') {
          out.push({ id: kb.id, name: kb.name })
        }
      } catch { /* skip */ }
    }
    workflowKbs.value = out
  } catch (e) {
    console.warn('load workflow KBs failed:', e)
  }
}
onMounted(() => {
  if (props.node.node_type === 'kb_writer') loadWorkflowKbs()
})
watch(() => props.node.node_type, (t) => {
  if (t === 'kb_writer' && workflowKbs.value.length === 0) loadWorkflowKbs()
})

// 知識庫 ID 陣列 ↔ 逗號字串 輔助
const kbIdsStr = ref((props.node.config.kb_ids ?? []).join(', '))
watch(() => props.node.config.kb_ids, (v) => {
  kbIdsStr.value = (v ?? []).join(', ')
})

function tryParseJson(event: Event, cb: (v: any) => void) {
  try {
    cb(JSON.parse((event.target as HTMLTextAreaElement).value))
  } catch { /* ignore invalid JSON */ }
}
</script>

<style scoped>
.form-label {
  @apply block text-xs font-semibold text-fg-secondary mb-1;
}
.form-input {
  @apply w-full text-sm border border-neutral-200 rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition;
}
</style>
