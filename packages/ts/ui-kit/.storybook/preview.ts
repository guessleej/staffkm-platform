import type { Preview } from '@storybook/vue3'
import { withThemeByClassName } from '@storybook/addon-themes'
import '@staffkm/design-tokens/css'
import './preview.css'

const preview: Preview = {
  parameters: {
    backgrounds: { default: 'surface', values: [
      { name: 'surface', value: 'hsl(var(--color-surface-base))' },
      { name: 'white',   value: '#ffffff' },
      { name: 'dark',    value: 'hsl(var(--color-neutral-950))' },
    ]},
    layout: 'centered',
    controls: { expanded: true },
  },
  decorators: [
    withThemeByClassName({
      themes: { light: '', dark: 'dark' },
      defaultTheme: 'light',
    }),
  ],
}
export default preview
