<!--
  v5.9.31 MarkdownMessage — 把 LLM 回覆的 markdown 渲染成漂亮排版
  - 用 marked (md-vendor chunk，跟 ArtifactPane 共用)
  - .md-body 樣式：標題 / 粗體 / 清單 / 程式碼 / 表格 / 引用
  - 串流中也即時渲染（content 變動 → computed 重算）
-->
<template>
  <div class="md-body text-sm text-fg w-full" v-html="rendered" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ content: string }>()

marked.setOptions({ breaks: true, gfm: true })

const rendered = computed(() => {
  const src = props.content || ''
  try {
    return marked.parse(src, { async: false }) as string
  } catch {
    // 解析失敗 → 退回純文字（保留換行）
    return src.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>')
  }
})
</script>

<style scoped>
/* 聊天訊息 markdown 排版 — 緊湊但分明 */
.md-body                     { word-break: break-word; overflow-wrap: anywhere; }
.md-body :deep(p)            { margin: 0.35rem 0; line-height: 1.65; }
.md-body :deep(p:first-child){ margin-top: 0; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(h1),
.md-body :deep(h2),
.md-body :deep(h3),
.md-body :deep(h4)           { font-weight: 700; margin: 0.8rem 0 0.4rem; line-height: 1.3; }
.md-body :deep(h1)           { font-size: 1.15rem; }
.md-body :deep(h2)           { font-size: 1.08rem; }
.md-body :deep(h3)           { font-size: 1rem; }
.md-body :deep(strong)       { font-weight: 700; color: hsl(var(--color-text-primary)); }
.md-body :deep(ul),
.md-body :deep(ol)           { margin: 0.4rem 0; padding-left: 1.4rem; }
.md-body :deep(li)           { margin: 0.2rem 0; line-height: 1.6; }
.md-body :deep(ul)           { list-style: disc; }
.md-body :deep(ol)           { list-style: decimal; }
.md-body :deep(a)            { color: hsl(var(--color-brand-600)); text-decoration: underline; }
.md-body :deep(code)         {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85em;
  background: hsl(var(--color-surface-sunken));
  padding: 0.1rem 0.35rem; border-radius: 0.3rem;
}
.md-body :deep(pre)          {
  background: hsl(var(--color-surface-sunken));
  padding: 0.75rem 0.9rem; border-radius: 0.6rem;
  overflow-x: auto; margin: 0.5rem 0;
}
.md-body :deep(pre code)     { background: none; padding: 0; }
.md-body :deep(blockquote)   {
  border-left: 3px solid hsl(var(--color-brand-300));
  padding-left: 0.8rem; margin: 0.5rem 0; color: hsl(var(--color-text-secondary));
}
.md-body :deep(table)        { border-collapse: collapse; margin: 0.5rem 0; width: 100%; font-size: 0.9em; }
.md-body :deep(th),
.md-body :deep(td)           { border: 1px solid hsl(var(--color-border-default)); padding: 0.35rem 0.6rem; text-align: left; }
.md-body :deep(th)           { background: hsl(var(--color-surface-sunken)); font-weight: 600; }
.md-body :deep(hr)           { border: none; border-top: 1px solid hsl(var(--color-border-default)); margin: 0.8rem 0; }
</style>
