import type { StorybookConfig } from '@storybook/vue3-vite'
import vue from '@vitejs/plugin-vue'

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(ts|tsx|mdx)'],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-themes',
  ],
  framework: { name: '@storybook/vue3-vite', options: {} },
  docs: { autodocs: 'tag' },
  typescript: { reactDocgen: false as any },
  /**
   * storybook 8 + vite 6 不會自動掛 @vitejs/plugin-vue；
   * 必須在 viteFinal 顯式注入，否則 .vue 檔被當成 JS parse → fail。
   */
  async viteFinal(config) {
    const hasVue = (config.plugins || []).some((p: any) =>
      p && (p.name === 'vite:vue' || (Array.isArray(p) && p.some((x: any) => x?.name === 'vite:vue')))
    )
    if (!hasVue) {
      config.plugins = [...(config.plugins || []), vue()]
    }
    return config
  },
}
export default config
