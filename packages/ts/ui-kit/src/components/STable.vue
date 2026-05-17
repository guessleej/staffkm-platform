<template>
  <div class="bg-surface-raised rounded-2xl border border-neutral-200 overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="bg-neutral-50 border-b border-neutral-100">
          <tr class="text-left text-[11px] text-neutral-500 uppercase tracking-wider">
            <th v-if="selectable" class="px-3 py-3 w-10">
              <slot name="header-checkbox"/>
            </th>
            <th v-for="c in columns" :key="c.key"
                :class="['px-4 py-3 font-semibold whitespace-nowrap',
                         c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : '',
                         c.width || '']">
              {{ c.label }}
            </th>
            <th v-if="$slots['header-actions']" class="px-4 py-3 w-px"><slot name="header-actions"/></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="totalCols" class="px-4 py-12 text-center text-xs text-neutral-400">載入中…</td>
          </tr>
          <tr v-else-if="!rows.length">
            <td :colspan="totalCols" class="px-4 py-12 text-center"><slot name="empty">尚無資料</slot></td>
          </tr>
          <tr v-for="(r, i) in rows" :key="rowKey ? r[rowKey] : i"
              :class="['transition-colors',
                       isSelected?.(r) ? 'bg-brand-50/40' : 'hover:bg-neutral-50/60',
                       'border-b border-neutral-50 last:border-0']">
            <td v-if="selectable" class="px-3 py-3"><slot name="row-checkbox" :row="r" :index="i"/></td>
            <td v-for="c in columns" :key="c.key"
                :class="['px-4 py-3',
                         c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : '',
                         c.cellClass || '']">
              <slot :name="`cell:${c.key}`" :row="r" :value="r[c.key]">{{ r[c.key] }}</slot>
            </td>
            <td v-if="$slots.actions" class="px-4 py-3 text-right">
              <slot name="actions" :row="r" :index="i"/>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface Column {
  key:    string
  label:  string
  width?: string
  align?: 'left' | 'right' | 'center'
  cellClass?: string
}

const props = defineProps<{
  columns:   Column[]
  rows:      any[]
  loading?:  boolean
  selectable?: boolean
  rowKey?:   string
  isSelected?: (r: any) => boolean
}>()

const totalCols = computed(() => props.columns.length + (props.selectable ? 1 : 0) + 1)
</script>
