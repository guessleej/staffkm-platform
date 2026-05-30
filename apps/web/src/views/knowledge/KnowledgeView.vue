<template>
  <div class="flex h-full">
    <!-- 左側資料夾樹（C-3）-->
    <aside class="w-60 border-r border-neutral-200 bg-surface-raised flex flex-col flex-shrink-0">
      <div class="px-3 py-3 border-b border-neutral-100 flex items-center justify-between">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-neutral-500">
          資料夾
        </h2>
        <button
          @click="showNewFolder = true"
          class="w-6 h-6 flex items-center justify-center rounded-md text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition"
          title="新增資料夾"
        >
          <IconPlus :size="12" :stroke-width="2.5" />
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto py-2 px-2">
        <!-- 根目錄 -->
        <button
          @click="activeFolderId = null"
          class="w-full flex items-center gap-1 px-2 py-1.5 rounded-md text-sm transition-colors mb-0.5"
          :class="activeFolderId === null
            ? 'bg-neutral-100 text-neutral-900'
            : 'text-neutral-700 hover:bg-neutral-50'"
        >
          <span class="w-4 h-4"></span>
          <svg class="w-3.5 h-3.5 text-neutral-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z"/>
          </svg>
          <span class="truncate flex-1 text-left">所有知識庫</span>
          <span class="text-[10px] text-neutral-400">{{ kbs.length }}</span>
        </button>

        <FolderTree
          :nodes="folderTreeData"
          :active-id="activeFolderId"
          @select="(n) => activeFolderId = n.id"
        />
      </nav>
    </aside>

    <!-- 主內容 -->
    <div class="flex-1 flex flex-col view-stagger">
      <!-- 頁首（v5.1 Warm Enterprise hero）-->
      <div class="px-6 pt-6 pb-5 bg-transparent flex-shrink-0 stagger-item-1">
       <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">{{ activeFolderName }}</h1>
          <p class="text-sm text-fg-tertiary mt-1.5 ml-[1rem]">{{ $t('knowledge.docCount', { n: filteredKbs.length }) }}</p>
          <!-- D-6：Project 過濾指示 -->
          <div
            v-if="activeProject"
            class="mt-2 inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-brand-50 text-brand-700 text-[11px]"
          >
            <span>{{ activeProject.emoji || '#' }}</span>
            <span>Project：{{ activeProject.name }}</span>
            <button @click="projects.switchTo(null)" class="text-brand-500 hover:text-brand-700">×</button>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <!-- v2.8 H1：匯入整個 KB -->
          <button
            @click="($refs.kbImportInput as HTMLInputElement)?.click()"
            class="inline-flex items-center gap-1.5 h-9 px-3 text-sm font-medium text-neutral-700 bg-surface-raised border border-neutral-200 hover:border-brand-400 hover:text-brand-600 rounded-lg transition-colors"
            title="從 zip 匯入 KB（建新 KB，不覆蓋）"
          >匯入</button>
          <input
            ref="kbImportInput"
            type="file"
            accept=".zip"
            class="hidden"
            @change="onKbImportSelected"
          />
          <button
            @click="showCreate = true"
            class="btn btn-primary"
          >
            <IconPlus :size="14" :stroke-width="2.5" />
            {{ $t('knowledge.createKb') }}
          </button>
        </div>
       </div>
      </div>

      <!-- 列表 -->
      <div class="flex-1 overflow-auto p-6 stagger-item-2">
        <div v-if="loading" class="flex items-center justify-center py-20 text-neutral-400 gap-2 text-sm">
          <IconSpinner :size="16" /> 載入中
        </div>

        <EmptyState v-else-if="!filteredKbs.length"
                icon="book-open"
                title="尚未建立知識庫"
                description="建立一個知識庫，再上傳文件、設定檢索方式"
                action-label="建立第一個"
                @action="showCreate = true" />

        <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div
            v-for="(kb, idx) in filteredKbs"
            :key="kb.id"
            class="card-warm fade-up relative overflow-hidden group"
            :style="{ animationDelay: (idx * 40) + 'ms' }"
            :class="batch.isSelected(kb.id) ? 'border-brand-400 ring-1 ring-brand-200' : ''"
          >
            <!-- v5.9.18: checkbox 重設計
                 - 平時真隱形 (無 border / 無 bg)，hover 才浮現
                 - 移到 icon 內部 — hover 時取代 IconKnowledge 顯示
                 - 選中時恆顯 brand 色實心
                 不再跟右上「正常」狀態 badge 撞位 -->
            <button
              class="absolute top-[18px] left-[18px] z-10 w-9 h-9 flex items-center justify-center rounded-lg
                     transition-all duration-150"
              :class="batch.isSelected(kb.id)
                ? 'bg-brand-600 text-white opacity-100 shadow-sm'
                : 'bg-white/85 backdrop-blur-sm ring-1 ring-brand-300 text-brand-600 opacity-0 group-hover:opacity-100'"
              @click.stop="batch.toggle(kb.id)"
              :title="batch.isSelected(kb.id) ? '取消選取' : '選取此 KB'"
              :aria-pressed="batch.isSelected(kb.id)"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            </button>

            <div class="px-5 pt-5 pb-4">
              <div class="flex items-start justify-between mb-3 gap-3">
                <div class="flex items-start gap-3 min-w-0">
                  <div class="w-9 h-9 rounded-lg flex items-center justify-center text-brand-600 bg-brand-50 flex-shrink-0">
                    <IconKnowledge :size="18" />
                  </div>
                  <div class="min-w-0">
                    <h3 class="font-semibold text-sm text-neutral-900 truncate">{{ kb.name }}</h3>
                    <p class="text-[11px] text-neutral-400 mt-0.5 font-mono">{{ kb.id.slice(0, 8) }}</p>
                  </div>
                </div>
                <span class="text-[11px] px-2 py-0.5 rounded-full font-medium flex-shrink-0" :class="statusClass(kb.status)">
                  {{ statusLabel(kb.status) }}
                </span>
              </div>
              <p class="text-xs text-neutral-500 line-clamp-2 min-h-[32px]">
                {{ kb.description || '尚未填寫說明' }}
              </p>
              <!-- 18-C：來源 badge -->
              <div v-if="kb.source_type === 'web' && kb.source_url" class="mt-2 flex items-center gap-1.5 text-[11px] text-fg-tertiary">
                <span>🌐</span>
                <a
                  :href="kb.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="truncate hover:text-brand-600"
                  @click.stop
                >{{ kb.source_url }}</a>
                <span v-if="kb.sync_status === 'running' || kb.sync_status === 'pending'"
                      class="ml-auto text-warning-600 flex-shrink-0">同步中</span>
                <span v-else-if="kb.sync_status === 'failed'"
                      class="ml-auto text-danger-600 flex-shrink-0">失敗</span>
              </div>
              <div v-else-if="kb.source_type === 'workflow'" class="mt-2 flex items-center gap-1.5 text-[11px] text-fg-tertiary">
                <span>⚡</span>
                <span>Workflow 寫入</span>
              </div>
            </div>
            <!-- v5.9.21: 一鍵建立綁定此 KB 的 RAG 對話助理 -->
            <div class="px-3 pt-0 pb-2">
              <button
                @click="onCreateRagApp(kb)"
                :disabled="ragBusyKbId === kb.id"
                class="w-full flex items-center justify-center gap-1.5 text-xs font-semibold text-white
                       bg-gradient-to-r from-brand-500 to-brand-700 hover:from-brand-600 hover:to-brand-800
                       py-2 rounded-lg transition disabled:opacity-50"
                title="自動建立一個只查此知識庫的 RAG 對話助理"
              >
                <SIcon :name="ragBusyKbId === kb.id ? 'loader' : 'sparkles'" :size="14"
                       :class="ragBusyKbId === kb.id ? 'animate-spin' : ''" />
                {{ ragBusyKbId === kb.id ? '建立中…' : '建立 RAG 對話助理' }}
              </button>
            </div>
            <div class="px-3 pb-3 pt-0 flex gap-1.5">
              <router-link
                :to="`/knowledge/${kb.id}/documents`"
                class="flex-1 text-center text-xs font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition-colors"
              >文件</router-link>
              <router-link
                :to="`/knowledge/${kb.id}/hit-test`"
                class="flex-1 text-center text-xs font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition-colors"
              >檢索測試</router-link>
              <!-- v5.11.x：GraphRAG 知識圖譜 -->
              <button
                @click.stop="openGraph(kb)"
                class="px-2 rounded-md transition-colors"
                :class="kb.graph_enabled ? 'text-brand-600 bg-brand-50 hover:bg-brand-100' : 'text-neutral-400 hover:text-brand-600 hover:bg-brand-50'"
                :title="kb.graph_enabled ? '知識圖譜（已啟用）' : '知識圖譜（未啟用）'"
              >
                <SIcon name="share-2" :size="14" />
              </button>
              <!-- Sprint 19-A：加入 Project -->
              <AttachToProjectButton kind="kb" :resource-id="kb.id" />
              <button
                @click="openAclDrawer(kb)"
                class="px-2 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded-md transition-colors"
                title="資源授權 / 關聯資源"
              >
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 11c0-1.66-1.34-3-3-3S6 9.34 6 11s1.34 3 3 3 3-1.34 3-3zm-3-5a5 5 0 100 10 5 5 0 000-10zm0 11c-3.31 0-6 2.69-6 6h12c0-3.31-2.69-6-6-6z"/>
                </svg>
              </button>
              <button
                @click="onConvertToWorkflow(kb)"
                class="px-2 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded-md transition-colors"
                title="轉換為工作流知識庫（不可撤回）"
              >
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
              </button>
              <button
                @click="relationsDrawerKb = kb"
                class="px-2 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded-md transition-colors"
                title="關聯資源（誰在用 / 用了誰）"
              >
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 015.656 5.656l-1.414 1.414m-5.656-5.656l-1.414 1.414a4 4 0 105.656 5.656"/>
                </svg>
              </button>
              <button
                @click="onExportKb(kb)"
                class="px-2 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded-md transition-colors"
                title="匯出整個 KB（含 metadata + paragraphs）"
              >
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                </svg>
              </button>
              <button
                @click="deleteKB(kb.id)"
                class="px-2 text-neutral-400 hover:text-danger-600 hover:bg-danger-50 rounded-md transition-colors"
                title="刪除"
              >
                <IconDelete :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 建立 KB Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showCreate"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/40 backdrop-blur-sm"
        @click.self="showCreate = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="font-semibold text-base text-neutral-900">建立知識庫</h3>
            <button @click="showCreate = false" class="p-1 rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100">
              <IconClose :size="14" />
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            <!-- Sprint 16：建立方式 tab -->
            <div class="inline-flex p-1 bg-neutral-100 rounded-lg gap-1">
              <button
                type="button"
                @click="createMode = 'manual'"
                class="px-3 py-1.5 text-xs font-medium rounded-md transition"
                :class="createMode === 'manual'
                  ? 'bg-surface-raised text-brand-700 shadow-sm'
                  : 'text-neutral-600 hover:text-neutral-900'"
              >📁 手動上傳</button>
              <button
                type="button"
                @click="createMode = 'web'"
                class="px-3 py-1.5 text-xs font-medium rounded-md transition"
                :class="createMode === 'web'
                  ? 'bg-surface-raised text-brand-700 shadow-sm'
                  : 'text-neutral-600 hover:text-neutral-900'"
              >🌐 從 URL 匯入</button>
            </div>

            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">
                名稱 <span class="text-danger-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                placeholder="例：人事法規、採購規範"
                class="form-input"
                @keyup.enter="onNameEnter"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">說明</label>
              <textarea
                v-model="form.description"
                rows="3"
                placeholder="這個知識庫的用途、適用對象等"
                class="form-textarea"
              />
            </div>

            <!-- Sprint 16 / 18-C / 19.x：Web 模式 URL 欄位 + sitemap 子模式 -->
            <div v-if="createMode === 'web'">
              <!-- 子模式切換 -->
              <div class="inline-flex p-0.5 bg-neutral-100 rounded-md gap-0.5 mb-2">
                <button type="button" @click="webSubMode = 'urls'"
                        class="px-2.5 py-1 text-[11px] rounded transition"
                        :class="webSubMode === 'urls' ? 'bg-surface-raised text-brand-700 shadow-sm font-medium' : 'text-fg-tertiary'">
                  📝 URL 清單
                </button>
                <button type="button" @click="webSubMode = 'sitemap'"
                        class="px-2.5 py-1 text-[11px] rounded transition"
                        :class="webSubMode === 'sitemap' ? 'bg-surface-raised text-brand-700 shadow-sm font-medium' : 'text-fg-tertiary'">
                  🗺️ sitemap.xml
                </button>
              </div>

              <div v-if="webSubMode === 'urls'">
                <label class="block text-xs font-semibold text-neutral-600 mb-1.5">
                  來源 URL <span class="text-danger-500">*</span>
                  <span class="text-fg-tertiary font-normal ml-1">（每行一個，最多 20）</span>
                </label>
                <textarea
                  v-model="form.web_url"
                  rows="3"
                  placeholder="https://docs.example.com/handbook&#10;https://docs.example.com/faq"
                  class="form-textarea font-mono"
                />
                <p v-if="urlCount > 0" class="text-[11px] text-brand-700 mt-1">
                  準備同步 <strong>{{ urlCount }}</strong> 個 URL
                </p>
              </div>

              <div v-else>
                <label class="block text-xs font-semibold text-neutral-600 mb-1.5">
                  sitemap.xml URL <span class="text-danger-500">*</span>
                </label>
                <input
                  v-model="form.sitemap_url"
                  type="url"
                  placeholder="https://docs.example.com/sitemap.xml"
                  class="form-input font-mono" />
                <div class="grid grid-cols-2 gap-3 mt-2">
                  <div>
                    <label class="block text-[11px] text-fg-tertiary mb-1">最大 URL 數</label>
                    <input v-model.number="form.sitemap_max" type="number" min="1" max="100"
                           class="form-input font-mono" />
                  </div>
                  <div>
                    <label class="block text-[11px] text-fg-tertiary mb-1">URL 子字串 filter（選填）</label>
                    <input v-model="form.sitemap_filter" placeholder="例：/docs/"
                           class="form-input font-mono" />
                  </div>
                </div>
                <p class="text-[11px] text-fg-tertiary mt-2">
                  自動解析 sitemap → 篩選 → 排程 N 個抓取任務。支援 sitemap-index（recursive 一層）。
                </p>
              </div>
            </div>

            <!-- 切片策略（RFC-006）─────────────────────────────────── -->
            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">
                切片策略
              </label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="opt in CHUNK_STRATEGIES" :key="opt.value"
                  type="button"
                  @click="form.chunk_strategy = opt.value"
                  class="text-left px-3 py-2 rounded-lg border text-xs transition"
                  :class="form.chunk_strategy === opt.value
                    ? 'border-brand-400 bg-brand-50 text-brand-700'
                    : 'border-neutral-200 hover:border-brand-300 text-neutral-700'"
                >
                  <div class="font-semibold">{{ opt.label }}</div>
                  <div class="text-[10px] text-neutral-500 mt-0.5">{{ opt.desc }}</div>
                </button>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-semibold text-neutral-600 mb-1">每段字數</label>
                <input
                  v-model.number="form.chunk_size" type="number" min="128" max="2048"
                  class="form-input"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold text-neutral-600 mb-1">overlap</label>
                <input
                  v-model.number="form.chunk_overlap" type="number" min="0" max="512"
                  class="form-input"
                />
              </div>
            </div>

            <p v-if="activeFolderId" class="text-[11px] text-neutral-500">
              將建立於資料夾「{{ activeFolderName }}」
            </p>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex items-center justify-end gap-2">
            <button
              @click="showCreate = false"
              class="h-9 px-4 text-sm text-neutral-700 bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
            >取消</button>
            <button
              @click="createKB"
              :disabled="!form.name || submitting || (createMode === 'web' && webSubMode === 'urls' && urlCount === 0) || (createMode === 'web' && webSubMode === 'sitemap' && !form.sitemap_url.trim())"
              class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg"
            >{{
              submitting
                ? '建立中…'
                : (createMode === 'web'
                    ? (webSubMode === 'sitemap'
                        ? '建立並解析 sitemap'
                        : urlCount > 1 ? `建立並抓取 ${urlCount} 個 URL` : '建立並開始抓取')
                    : '建立')
            }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- 建立 Folder Modal -->
  <Teleport to="body">
    <div
      v-if="showNewFolder"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/40 backdrop-blur-sm"
      @click.self="showNewFolder = false"
    >
      <div class="w-full max-w-sm bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100">
          <h3 class="font-semibold text-sm text-neutral-900">新增資料夾</h3>
        </div>
        <div class="px-5 py-4">
          <input
            v-model="folderForm.name"
            placeholder="例：人事 / 採購 / 法規"
            class="form-input"
            @keyup.enter="createFolder"
          />
          <p v-if="activeFolderId" class="text-[11px] text-neutral-500 mt-2">
            將建立於「{{ activeFolderName }}」之下
          </p>
        </div>
        <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2">
          <button
            @click="showNewFolder = false"
            class="h-9 px-4 text-sm text-neutral-700 bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
          >取消</button>
          <button
            :disabled="!folderForm.name.trim()"
            @click="createFolder"
            class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg"
          >建立</button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 批量選擇浮動工具列 -->
  <BatchSelectToolbar :count="batch.count" @clear="batch.clear()">
    <button
      @click="batchDelete"
      class="px-2.5 py-1.5 rounded-lg text-sm text-white/90 hover:bg-white/10 hover:text-white transition"
    >刪除</button>
  </BatchSelectToolbar>

  <!-- v2.1 11-4：資源授權 / 關聯資源抽屜 -->
  <KbAccessDrawer
    v-if="aclKb"
    :open="aclOpen"
    :kb-id="aclKb.id"
    :kb-name="aclKb.name"
    @update:open="(v: boolean) => (aclOpen = v)"
  />

  <!-- MaxKB v2.9 對齊：關聯資源側邊抽屜 -->
  <Teleport to="body">
    <div
      v-if="relationsDrawerKb"
      class="fixed inset-0 z-50 flex justify-end"
      @click.self="relationsDrawerKb = null"
    >
      <div class="absolute inset-0 bg-black/30" @click="relationsDrawerKb = null"></div>
      <aside class="relative w-80 h-full bg-surface-raised shadow-xl flex flex-col">
        <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          <div class="min-w-0">
            <h3 class="text-sm font-semibold text-neutral-900 truncate">關聯資源</h3>
            <p class="text-[11px] text-neutral-500 truncate">{{ relationsDrawerKb.name }}</p>
          </div>
          <button @click="relationsDrawerKb = null" class="p-1 rounded-md text-neutral-400 hover:bg-neutral-100">
            <SIcon name="x" :size="16" />
          </button>
        </div>
        <div class="flex-1 overflow-hidden p-3">
          <ResourceRelationsPanel
            resource-type="knowledge_base"
            :resource-id="relationsDrawerKb.id"
          />
        </div>
      </aside>
    </div>
  </Teleport>

  <!-- v5.11.x：GraphRAG 知識圖譜 總覽 modal -->
  <Teleport to="body">
    <div v-if="graph.kb" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="graph.kb = null">
      <div class="absolute inset-0 bg-black/30" @click="graph.kb = null"></div>
      <div class="relative w-full max-w-2xl max-h-[85vh] bg-surface-raised rounded-2xl shadow-xl flex flex-col overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 border-b border-neutral-200">
          <div class="min-w-0">
            <h3 class="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <SIcon name="share-2" :size="16" /> 知識圖譜
            </h3>
            <p class="text-[11px] text-neutral-500 truncate">{{ graph.kb.name }}</p>
          </div>
          <button @click="graph.kb = null" class="p-1 rounded-md text-neutral-400 hover:bg-neutral-100"><SIcon name="x" :size="16" /></button>
        </div>

        <div class="flex-1 overflow-y-auto p-5 space-y-4">
          <div v-if="graph.loading" class="text-center py-8 text-fg-tertiary text-sm">載入中…</div>
          <template v-else-if="graph.overview">
            <!-- 計數 + 動作 -->
            <div class="flex items-center gap-4 flex-wrap">
              <div class="text-xs text-fg-secondary">狀態：
                <span :class="graph.overview.graph_enabled ? 'text-success-600' : 'text-fg-tertiary'">
                  {{ graph.overview.graph_enabled ? '已啟用' : '未啟用' }}
                </span>
              </div>
              <div class="flex gap-3 text-xs text-fg-secondary">
                <span>實體 <b>{{ graph.overview.entities }}</b></span>
                <span>關係 <b>{{ graph.overview.relations }}</b></span>
                <span>社群 <b>{{ graph.overview.total }}</b></span>
              </div>
              <div class="ml-auto flex gap-2">
                <button @click="graphRebuild" :disabled="graph.busy"
                        class="px-3 py-1.5 text-xs rounded-md bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50">
                  {{ graph.busy ? '排程中…' : (graph.overview.graph_enabled ? '重建圖譜' : '建立知識圖譜') }}
                </button>
                <button v-if="graph.overview.graph_enabled" @click="graphDisable" :disabled="graph.busy"
                        class="px-3 py-1.5 text-xs rounded-md border border-bd text-fg-secondary hover:bg-neutral-100 disabled:opacity-50">停用</button>
              </div>
            </div>
            <p v-if="graph.note" class="text-[11px] text-warning-700">{{ graph.note }}</p>

            <!-- 社群 -->
            <div v-if="graph.overview.communities.length" class="space-y-2">
              <div class="text-xs font-semibold text-fg-secondary">實體社群（連通分量 + 摘要）</div>
              <div v-for="c in graph.overview.communities" :key="c.id" class="border border-bd rounded-lg p-3">
                <div class="flex items-center gap-2 text-sm font-medium text-fg">
                  {{ c.title || '社群' }}
                  <span class="text-[11px] text-fg-tertiary">{{ c.size }} 實體 · 密度 {{ c.cohesion_score?.toFixed?.(2) ?? '—' }}</span>
                </div>
                <p v-if="c.summary" class="text-xs text-fg-secondary mt-1 leading-relaxed">{{ c.summary }}</p>
                <p class="text-[11px] text-fg-tertiary mt-1.5 truncate">{{ (c.entities || []).slice(0, 8).join('、') }}</p>
              </div>
            </div>
            <p v-else-if="graph.overview.graph_enabled" class="text-xs text-fg-tertiary">
              尚無社群（需有實體關係；點「重建圖譜」後背景處理，完成再開啟查看）。
            </p>
            <p v-else class="text-xs text-fg-tertiary">
              啟用後系統會用地端 LLM 對此 KB 的散文文件抽取實體/關係並分群（加法層，不影響既有檢索）。
            </p>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { knowledgeApi, type KbFolder } from '../../api/knowledge'
import { IconClose, IconDelete, IconKnowledge, IconPlus, IconSpinner } from '../../components/icons'
import { useBatchSelect } from '../../composables/useBatchSelect'
import BatchSelectToolbar from '../../components/common/BatchSelectToolbar.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import FolderTree, { type FolderNode } from '../../components/common/FolderTree.vue'
import KbAccessDrawer from '../../components/knowledge/KbAccessDrawer.vue'
import AttachToProjectButton from '../../components/project/AttachToProjectButton.vue'
import ResourceRelationsPanel from '../../components/common/ResourceRelationsPanel.vue'
import { SIcon } from '@staffkm/ui-kit'
import { useProjectStore } from '../../stores/project'
import { useRouter } from 'vue-router'
import { applicationApi } from '../../api/application'

const router = useRouter()

// v5.9.21: 一鍵把單一 KB 變成 RAG 對話助理
// ── GraphRAG 知識圖譜 modal（v5.11.x 可視化）──────────────────────
const graph = reactive<{ kb: any; loading: boolean; busy: boolean; note: string; overview: any }>({
  kb: null, loading: false, busy: false, note: '', overview: null,
})
async function loadGraphOverview() {
  if (!graph.kb) return
  graph.loading = true
  try { graph.overview = await knowledgeApi.getGraphOverview(graph.kb.id) }
  catch { graph.overview = { graph_enabled: false, entities: 0, relations: 0, total: 0, communities: [] } }
  finally { graph.loading = false }
}
async function openGraph(kb: any) {
  graph.kb = kb; graph.note = ''; graph.overview = null
  await loadGraphOverview()
}
async function graphRebuild() {
  if (!graph.kb || graph.busy) return
  graph.busy = true
  try {
    await knowledgeApi.rebuildGraph(graph.kb.id)
    graph.note = '已排程背景建圖（地端 LLM 抽取，需數分鐘）；完成後重開此視窗查看社群。'
    if (graph.overview) graph.overview.graph_enabled = true
  } catch (e: any) { graph.note = '建圖排程失敗：' + (e?.message || '') }
  finally { graph.busy = false }
}
async function graphDisable() {
  if (!graph.kb || graph.busy) return
  graph.busy = true
  try { await knowledgeApi.disableGraph(graph.kb.id); await loadGraphOverview() }
  finally { graph.busy = false }
}

const ragBusyKbId = ref<string | null>(null)
async function onCreateRagApp(kb: any) {
  if (ragBusyKbId.value) return
  ragBusyKbId.value = kb.id
  try {
    const { data } = await applicationApi.create({
      name: `${kb.name} 助理`,
      description: `從知識庫「${kb.name}」自動建立的 RAG 對話助理`,
      type: 'simple',
      system_prompt:
        `你是「${kb.name}」知識庫的專屬助理。請只根據提供的參考資料回答問題，` +
        `若資料中沒有明確答案，請誠實說明並提供一般性建議，不要編造內容。回答使用繁體中文。`,
      welcome_message: `你好！我會根據「${kb.name}」的內容回答你的問題，請問有什麼需要協助的嗎？`,
      knowledge_base_ids: [kb.id],
      is_public: false,
    })
    const appId = data?.data?.id || data?.id
    if (appId) {
      // v5.10.14：KB→RAG 後直接進統一「對話」（不再開獨立 ApplicationChatView）
      router.push({ path: '/chat', query: { app: appId, appName: `${kb.name} 助理` } })
    } else {
      alert('已建立 RAG 助理，請至「應用」頁查看')
    }
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '建立 RAG 助理失敗')
  } finally {
    ragBusyKbId.value = null
  }
}

const kbs = ref<any[]>([])
const folders = ref<KbFolder[]>([])
const loading = ref(true)
const showCreate = ref(false)
const showNewFolder = ref(false)
const form = ref({
  name: '',
  description: '',
  chunk_strategy: 'auto' as 'auto' | 'recursive' | 'markdown' | 'qa',
  chunk_size: 512,
  chunk_overlap: 64,
  web_url: '',
  sitemap_url: '',
  sitemap_max: 20,
  sitemap_filter: '',
})
const createMode = ref<'manual' | 'web'>('manual')
const webSubMode = ref<'urls' | 'sitemap'>('urls')
const submitting = ref(false)
// 18-C：解析 textarea 內的 URL 清單
const parsedUrls = computed<string[]>(() => {
  if (createMode.value !== 'web' || !form.value.web_url) return []
  return form.value.web_url
    .split(/[\n\r]+/)
    .map(s => s.trim())
    .filter(s => /^https?:\/\//i.test(s))
    .slice(0, 20)
})
const urlCount = computed(() => parsedUrls.value.length)

// 切片策略選項（RFC-006）
const CHUNK_STRATEGIES = [
  { value: 'auto',      label: '自動',     desc: '依內容自動偵測（推薦）' },
  { value: 'recursive', label: '遞迴字符', desc: '段→句→字回退；CJK 友好' },
  { value: 'markdown',  label: 'Markdown', desc: '保留 heading 階層脈絡' },
  { value: 'qa',        label: 'Q&A 對',   desc: 'FAQ / 問答格式文件' },
] as const
const folderForm = reactive({ name: '' })

const activeFolderId = ref<string | null>(null)

// ── 批量選擇 ───────────────────────────────────────────────────────────
const batch = useBatchSelect()

// ── D-6：Project 過濾 ─────────────────────────────────────────────────
const projects = useProjectStore()
const activeProject = computed(() => projects.active)

// ── computed ───────────────────────────────────────────────────────────
const filteredKbs = computed(() => {
  let list = kbs.value
  // 先依 Project（D-6），再依 Folder（C-3）
  if (activeProject.value) {
    const ids = new Set(activeProject.value.knowledge_base_ids || [])
    list = list.filter((k) => ids.has(k.id))
  }
  if (activeFolderId.value !== null) {
    list = list.filter((k) => k.folder_id === activeFolderId.value)
  }
  return list
})

const activeFolderName = computed(() => {
  if (activeFolderId.value === null) return '所有知識庫'
  return folders.value.find((f) => f.id === activeFolderId.value)?.name || '資料夾'
})

const folderTreeData = computed<FolderNode[]>(() => {
  // 把 flat folders 轉成 FolderNode tree
  const map: Record<string, FolderNode> = {}
  for (const f of folders.value) {
    map[f.id] = { id: f.id, name: f.name, count: f.kb_count, children: [] }
  }
  const roots: FolderNode[] = []
  for (const f of folders.value) {
    const node = map[f.id]
    if (f.parent_id && map[f.parent_id]) {
      map[f.parent_id].children!.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
})

// ── helpers ────────────────────────────────────────────────────────────
function statusClass(s: string) {
  return {
    active:   'bg-success-50 text-success-700',
    building: 'bg-warning-50 text-warning-700',
    error:    'bg-danger-50 text-danger-600',
    disabled: 'bg-neutral-100 text-neutral-500',
  }[s] ?? 'bg-neutral-100 text-neutral-500'
}
function statusLabel(s: string) {
  return { active: '正常', building: '建構中', error: '錯誤', disabled: '停用' }[s] ?? s
}

// ── data loading ───────────────────────────────────────────────────────
// 重試 + 永遠 finally 清 loading；避免 503 cold-start 後永遠卡在「載入中…」
async function load() {
  loading.value = true
  try {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const [kbData, folderData] = await Promise.all([
          knowledgeApi.listBases(),
          knowledgeApi.listFolders().catch(() => []),
        ])
        kbs.value = kbData.data || []
        folders.value = folderData
        return  // 成功就跳出（finally 仍會跑）
      } catch (e: any) {
        const status = e?.response?.status
        if (status && status < 500) throw e
        if (attempt === 2) throw e
        await new Promise(r => setTimeout(r, 800 * Math.pow(2, attempt)))
      }
    }
  } catch (e) {
    console.error('KnowledgeView load failed:', e)
  } finally {
    loading.value = false
  }
}

// v5.12: 名稱輸入框按 Enter 送出（只在 manual 模式 + 有名稱 + 非送出中；
//   web 模式還有 URL/sitemap 等必填欄位，不該在名稱按 Enter 就提前建立）。
function onNameEnter() {
  if (createMode.value === 'manual' && form.value.name.trim() && !submitting.value) {
    createKB()
  }
}

async function createKB() {
  if (submitting.value) return
  // v5.12: 前端驗證 — overlap 必須小於 size，否則送壞值給後端
  if (form.value.chunk_overlap >= form.value.chunk_size) {
    alert('分塊重疊（chunk overlap）必須小於分塊大小（chunk size）')
    return
  }
  submitting.value = true
  try {
    const res: any = await knowledgeApi.createBase({
      name: form.value.name,
      description: form.value.description || undefined,
      folder_id: activeFolderId.value,
      chunk_strategy: form.value.chunk_strategy,
      chunk_size: form.value.chunk_size,
      chunk_overlap: form.value.chunk_overlap,
    })
    // Web 模式：再 trigger 同步任務
    if (createMode.value === 'web') {
      const kbId = res?.id || res?.data?.id
      if (kbId) {
        try {
          if (webSubMode.value === 'sitemap' && form.value.sitemap_url) {
            const r = await knowledgeApi.syncFromSitemap(kbId, {
              sitemap_url: form.value.sitemap_url.trim(),
              max_urls: form.value.sitemap_max || 20,
              url_filter: form.value.sitemap_filter.trim() || undefined,
            })
            alert(`從 sitemap 找到 ${r.url_count} 個 URL，已排程同步`)
          } else if (parsedUrls.value.length === 1) {
            await knowledgeApi.syncFromWeb(kbId, parsedUrls.value[0])
          } else if (parsedUrls.value.length > 1) {
            await knowledgeApi.syncFromWebBatch(kbId, parsedUrls.value)
          }
        } catch (e: any) {
          alert(`KB 已建立，但啟動 URL 同步失敗：${e?.response?.data?.detail || e?.message || ''}`)
        }
      }
    }
    showCreate.value = false
    form.value = { name: '', description: '', chunk_strategy: 'auto', chunk_size: 512, chunk_overlap: 64, web_url: '', sitemap_url: '', sitemap_max: 20, sitemap_filter: '' }
    createMode.value = 'manual'
    webSubMode.value = 'urls'
    await load()
    // v5.12: 若有「啟用中的專案」且新 KB 不在該專案範圍 → filteredKbs 會把它藏起來（看似建了就消失）。
    //   切回「所有知識庫」檢視讓使用者看得到剛建的 KB。
    const newId = res?.id || res?.data?.id
    if (newId && projects.active && !(projects.active.knowledge_base_ids || []).includes(newId)) {
      projects.activeId = null
      alert('已建立知識庫。已切換到「所有知識庫」檢視（新知識庫不屬於目前啟用的專案）。')
    }
  } catch (e: any) {
    // v5.12: 補 catch — 建 KB 失敗（重名/500）原本無提示、modal 不關，使用者重複按不知原因
    alert(`建立知識庫失敗：${e?.response?.data?.detail || e?.response?.data?.message || e?.message || '請稍後再試'}`)
  } finally {
    submitting.value = false
  }
}

async function deleteKB(id: string) {
  if (!confirm('確定要刪除？其下的文件與向量資料會一併移除。')) return
  try {
    await knowledgeApi.deleteBase(id)
    await load()
  } catch (e: any) {
    alert(`刪除失敗：${e?.response?.data?.detail || e?.message || '請稍後再試'}`)
  }
}

// ── v2.8 H1：整 KB 匯出 / 匯入 ────────────────────────────────────
async function onExportKb(kb: any) {
  try {
    const includeEmb = confirm(`匯出「${kb.name}」？\n按「確定」連 embeddings 一起匯出（檔案會比較大）；按「取消」只匯 metadata。`)
    const blob = await knowledgeApi.exportKb(kb.id, includeEmb)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `kb-${kb.id}.full.zip`
    document.body.appendChild(a); a.click()
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url) }, 100)
  } catch (e: any) {
    alert('匯出失敗：' + (e?.response?.data?.detail || e?.message))
  }
}
async function onKbImportSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  const rename = prompt('（選填）匯入後重新命名 KB；留空則沿用 zip 內名稱：', '') || undefined
  try {
    const r = await knowledgeApi.importKb(file, rename)
    alert(`匯入完成：新 KB ${r.kb_id}（${r.documents} docs / ${r.paragraphs} paragraphs）。\n段落尚未 embed，可至文件頁手動觸發 re-embed。`)
    await load()
  } catch (err: any) {
    alert('匯入失敗：' + (err?.response?.data?.detail || err?.message))
  }
}

// ── v2.1 11-4：資源授權抽屜 + 轉換為工作流 KB ──────────────────────
const aclOpen = ref(false)
const aclKb = ref<{ id: string; name: string } | null>(null)

// 關聯資源抽屜（MaxKB v2.9 對齊）
const relationsDrawerKb = ref<{ id: string; name: string } | null>(null)

function openAclDrawer(kb: any) {
  aclKb.value = { id: kb.id, name: kb.name }
  aclOpen.value = true
}

async function onConvertToWorkflow(kb: any) {
  const wf = prompt(
    `要將「${kb.name}」轉換為工作流知識庫（不可撤回）。\n` +
    `請輸入來源 workflow ID（即 application ID，由其 workflow 寫入此 KB）：`,
    ''
  )
  if (!wf) return
  if (!confirm(`確定？轉換後此 KB 將鎖定為 workflow KB，後續寫入只能透過該 workflow 的 kb_writer 節點。`)) return
  try {
    await knowledgeApi.convertToWorkflowKB(kb.id, wf.trim())
    alert('已轉換為 workflow KB')
    await load()
  } catch (e: any) {
    alert('轉換失敗：' + (e?.response?.data?.detail || e?.message))
  }
}

async function batchDelete() {
  const ids = Array.from(batch.selected.value)
  if (ids.length === 0) return
  if (!confirm(`確定要刪除 ${ids.length} 個知識庫？其下的文件與向量資料會一併移除。`)) return
  for (const id of ids) {
    try { await knowledgeApi.deleteBase(id) } catch { /* swallow */ }
  }
  batch.clear()
  await load()
}

async function createFolder() {
  const name = folderForm.name.trim()
  if (!name) return
  try {
    await knowledgeApi.createFolder({ name, parent_id: activeFolderId.value })
    folderForm.name = ''
    showNewFolder.value = false
    await load()
  } catch (e) {
    console.error('create folder failed', e)
  }
}

onMounted(load)
</script>
