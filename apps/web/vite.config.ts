import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // 15-3: 把 LogicFlow (~500KB) 拆成獨立 chunk，避免 WorkflowEditorView
    // 卡 668KB 大包；Vue/router/pinia 也另成 vendor chunk
    rollupOptions: {
      output: {
        manualChunks: {
          // 15-3: 重型 vendors 拆獨立 chunk 利於長期 cache
          'lf-vendor':   ['@logicflow/core'],
          'vue-vendor':  ['vue', 'vue-router', 'pinia'],
          // 19-perf：marked + highlight.js (~400KB) 拆出，避免污染 ChatLayout
          'md-vendor':   ['marked', 'highlight.js'],
        },
      },
    },
    chunkSizeWarningLimit: 650,
  },
})
