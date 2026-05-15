import type { StorybookConfig } from '@storybook/vue3-vite'

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(ts|tsx|mdx)'],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-themes',
  ],
  framework: { name: '@storybook/vue3-vite', options: {} },
  docs: { autodocs: 'tag' },
  typescript: { reactDocgen: false as any },
}
export default config
