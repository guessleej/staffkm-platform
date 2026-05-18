<script setup lang="ts">
import { comparison } from '../data/pricing'
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full border-collapse text-sm">
      <thead>
        <tr class="border-b-2 border-ink-100">
          <th class="text-left py-4 px-4 font-medium text-ink-500">功能對比</th>
          <th class="py-4 px-4 font-semibold text-ink-900">Trial</th>
          <th class="py-4 px-4 font-semibold text-ink-900">Starter</th>
          <th class="py-4 px-4 font-semibold text-brand-600">Pro</th>
          <th class="py-4 px-4 font-semibold text-ink-900">Enterprise</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in comparison"
          :key="row.feature"
          class="border-b border-ink-100"
        >
          <td class="py-3 px-4 text-ink-700">{{ row.feature }}</td>
          <td v-for="col in ['trial', 'starter', 'pro', 'enterprise'] as const" :key="col" class="py-3 px-4 text-center">
            <template v-if="typeof row[col] === 'boolean'">
              <span v-if="row[col]" class="text-brand-600 font-bold">✓</span>
              <span v-else class="text-ink-300">—</span>
            </template>
            <template v-else>
              <span class="text-ink-700">{{ row[col] }}</span>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
