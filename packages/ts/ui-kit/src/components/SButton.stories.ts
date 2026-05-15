import type { Meta, StoryObj } from '@storybook/vue3'
import SButton from './SButton.vue'

const meta: Meta<typeof SButton> = {
  title: 'Components/SButton',
  component: SButton,
  tags: ['autodocs'],
  argTypes: {
    variant: { control: 'select', options: ['primary', 'secondary', 'ghost', 'danger', 'link'] },
    size:    { control: 'select', options: ['sm', 'md', 'lg'] },
    block:   { control: 'boolean' },
    loading: { control: 'boolean' },
    disabled: { control: 'boolean' },
  },
}
export default meta
type Story = StoryObj<typeof SButton>

export const Primary: Story = {
  args: { variant: 'primary' },
  render: (args) => ({ components: { SButton }, setup: () => ({ args }), template: `<SButton v-bind="args">儲存變更</SButton>` }),
}
export const Secondary: Story = { ...Primary, args: { variant: 'secondary' } }
export const Ghost: Story     = { ...Primary, args: { variant: 'ghost' } }
export const Danger: Story    = { ...Primary, args: { variant: 'danger' } }

export const AllVariants: Story = {
  render: () => ({
    components: { SButton },
    template: `
      <div class="flex flex-col gap-3">
        <div class="flex items-center gap-2">
          <SButton variant="primary">Primary</SButton>
          <SButton variant="secondary">Secondary</SButton>
          <SButton variant="ghost">Ghost</SButton>
          <SButton variant="danger">Danger</SButton>
          <SButton variant="link">Link</SButton>
        </div>
        <div class="flex items-center gap-2">
          <SButton size="sm">Small</SButton>
          <SButton size="md">Medium</SButton>
          <SButton size="lg">Large</SButton>
        </div>
        <div class="flex items-center gap-2">
          <SButton loading>Loading…</SButton>
          <SButton disabled>Disabled</SButton>
        </div>
      </div>
    `,
  }),
}
