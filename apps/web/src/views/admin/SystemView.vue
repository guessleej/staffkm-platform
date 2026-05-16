<template>
  <UnderConstructionView
    title="系統設定"
    description="調整全域偏好、預設嵌入模型、檔案上限、Hybrid Search 權重、安全策略等。目前此頁面尚在開發中。"
    :features="[
      '預設 embedding 模型 / reranker 設定',
      'Hybrid Search RRF 權重調整',
      '檔案上傳大小與型別白名單',
      '密碼策略、登入失敗鎖定',
      '備份 / 還原 / 匯出（後續 Phase）',
    ]"
  />
</template>

<script setup lang="ts">
import UnderConstructionView from '../../components/common/UnderConstructionView.vue'
</script>
