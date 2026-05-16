<template>
  <UnderConstructionView
    title="檢索測試"
    description="輸入問題，看看現有的知識庫會撈出哪些段落、相符度多高、reranker 後排序如何。用來調整 chunking 策略與 RRF 權重。目前此頁面尚在開發中。"
    :features="[
      '單一 KB 命中測試 + 相符度分數',
      '跨多 KB 同時檢索（合併排序）',
      'Hybrid Search 三權重視覺化（語意 / BM25 / 後排）',
      '命中段落高亮（顯示 char_start / char_end）',
      'A/B 比較不同 chunking 策略效果',
    ]"
  />
</template>

<script setup lang="ts">
import UnderConstructionView from '../../components/common/UnderConstructionView.vue'
</script>
