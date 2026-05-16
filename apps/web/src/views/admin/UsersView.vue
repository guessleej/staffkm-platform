<template>
  <UnderConstructionView
    title="使用者管理"
    description="管理員可在這裡新增 / 停用 / 修改使用者，指派 workspace 角色，並查看登入紀錄。目前此頁面尚在開發中。"
    :features="[
      '邀請新成員加入 workspace',
      '指派角色（owner / admin / editor / viewer）',
      '重設密碼、停用 / 啟用帳號',
      '查看最後登入時間與 audit 紀錄',
      'SSO / OIDC / LDAP 接入（後續 Phase）',
    ]"
  />
</template>

<script setup lang="ts">
import UnderConstructionView from '../../components/common/UnderConstructionView.vue'
</script>
