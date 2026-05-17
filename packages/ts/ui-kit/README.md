# @staffkm/ui-kit

Vue 3 component library — **34 components**, design-token aware, dark-mode ready.

## Browse the gallery

```bash
pnpm --filter @staffkm/ui-kit storybook
# → http://localhost:6006  (Overview / Gallery 一頁掃完)
```

## Catalog

| Category | Components |
|----------|-----------|
| Form | SInput · STextarea · SCheckbox · SRadio · SSwitch · SSelect · SSearchInput · SChipInput · SFileUpload |
| Display | SAvatar · SBadge · STag · SCard · SAlert · SEmpty · SStatCard · SSkeleton · SSpinner · SDivider · SKbd · SProgress |
| Navigation | SBreadcrumb · STabs · SPagination · SSegmented · SListItem · SToolbar · SSidebarSection |
| Overlay & Action | SButton · SIconButton · STooltip · SDropdown · SModal · SDrawer |
| Data | STable · SCodeBlock |
| Icon | SIcon (44 lucide-style names) |

## Usage

```vue
<script setup>
import { SButton, SIcon, SAlert } from '@staffkm/ui-kit'
</script>
<template>
  <SButton variant="primary">
    <SIcon name="plus" :size="16" /> 新增
  </SButton>
  <SAlert type="success" title="完成" />
</template>
```

## Design system layer

```
@staffkm/design-tokens  →  HSL CSS variables
@staffkm/ui-kit         →  Vue 3 components (this package)
apps/web                →  consumes both
```

Never hard-code `bg-white` / `text-gray-*` — use `bg-surface-raised` / `text-fg` aliases so dark-mode flip works without component changes.

## Known issue

`pnpm build-storybook` currently fails on `SButton.vue` line 10 parse error
under vite 6 + storybook 8. Dev (`pnpm storybook`) works fine.
