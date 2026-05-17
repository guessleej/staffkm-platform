/**
 * Gallery — 一頁瀏覽全部 34 個 ui-kit 元件
 * 啟動：`pnpm --filter @staffkm/ui-kit storybook`，瀏覽 Overview / Gallery
 */
import type { Meta, StoryObj } from '@storybook/vue3'
import {
  SAlert, SAvatar, SBadge, SButton, SCard, SEmpty, SInput, SModal, SSpinner,
  STag, STextarea,
  SCheckbox, SRadio, SSwitch, SSelect, SDivider, STabs, SPagination,
  SBreadcrumb, STooltip, SDropdown, SDrawer, SProgress, SSkeleton, SKbd,
  SStatCard, STable, SSegmented, SSearchInput, SChipInput, SFileUpload,
  SListItem, SToolbar, SCodeBlock, SIconButton, SSidebarSection, SIcon,
} from './index'

const meta: Meta = {
  title: 'Overview/Gallery',
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          '一頁掃完全部 34 個 ui-kit 元件。點各區塊跳到對應 story 看 props/source。',
      },
    },
  },
}
export default meta

type Story = StoryObj

const Section = (title: string, children: string) => `
  <section class="mb-10">
    <h2 class="text-lg font-semibold text-fg mb-3 border-b border-neutral-200 pb-2">${title}</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">${children}</div>
  </section>`

const Card = (label: string, slot: string) => `
  <div class="bg-surface-raised border border-neutral-200 rounded-xl p-4">
    <div class="text-xs text-fg-tertiary mb-2 font-mono">${label}</div>
    <div class="min-h-[60px] flex items-center gap-2 flex-wrap">${slot}</div>
  </div>`

export const All: Story = {
  render: () => ({
    components: {
      SAlert, SAvatar, SBadge, SButton, SCard, SEmpty, SInput, SSpinner,
      STag, STextarea, SCheckbox, SRadio, SSwitch, SSelect, SDivider, STabs,
      SPagination, SBreadcrumb, STooltip, SDropdown, SProgress, SSkeleton,
      SKbd, SStatCard, STable, SSegmented, SSearchInput, SChipInput,
      SFileUpload, SListItem, SToolbar, SCodeBlock, SIconButton,
      SSidebarSection, SIcon, SModal, SDrawer,
    },
    template: `
      <div class="p-8 bg-surface-base min-h-screen">
        <header class="mb-8">
          <h1 class="text-2xl font-bold text-fg">@staffkm/ui-kit Gallery</h1>
          <p class="text-sm text-fg-secondary mt-1">34 components · design-token aware · dark-mode ready</p>
        </header>

        ${Section('Form', [
          Card('SInput',    `<SInput placeholder="輸入..." />`),
          Card('STextarea', `<STextarea placeholder="多行文字" :rows="2" />`),
          Card('SCheckbox', `<SCheckbox :modelValue="true" label="同意條款" />`),
          Card('SRadio',    `<SRadio name="g" value="a" :modelValue="'a'" label="選項 A" />`),
          Card('SSwitch',   `<SSwitch :modelValue="true" />`),
          Card('SSelect',   `<SSelect :options="[{label:'A',value:1},{label:'B',value:2}]" />`),
          Card('SSearchInput', `<SSearchInput placeholder="搜尋..." />`),
          Card('SChipInput',   `<SChipInput :modelValue="['vue','ts']" />`),
          Card('SFileUpload',  `<SFileUpload />`),
        ].join(''))}

        ${Section('Display', [
          Card('SAvatar',   `<SAvatar name="Jeff" /><SAvatar src="https://i.pravatar.cc/40" />`),
          Card('SBadge',    `<SBadge>NEW</SBadge> <SBadge variant="success">OK</SBadge> <SBadge variant="danger">!</SBadge>`),
          Card('STag',      `<STag>tag</STag> <STag closable>removable</STag>`),
          Card('SCard',     `<SCard title="標題" subtitle="副標">內容區塊</SCard>`),
          Card('SAlert',    `<SAlert type="info" title="提示">提示訊息</SAlert>`),
          Card('SEmpty',    `<SEmpty title="尚無資料" />`),
          Card('SStatCard', `<SStatCard label="總文件" :value="1234" format="number" />`),
          Card('SSkeleton', `<SSkeleton :width="200" :height="12" /><br/><SSkeleton :width="120" :height="12" />`),
          Card('SSpinner',  `<SSpinner :size="24" />`),
          Card('SDivider',  `<SDivider /> <SDivider>中間文字</SDivider>`),
          Card('SKbd',      `<SKbd>⌘</SKbd> <SKbd>K</SKbd>`),
          Card('SProgress', `<SProgress :value="65" />`),
        ].join(''))}

        ${Section('Navigation', [
          Card('SBreadcrumb', `<SBreadcrumb :items="[{label:'首頁',to:'/'},{label:'目錄'},{label:'詳情'}]" />`),
          Card('STabs',       `<STabs :tabs="[{key:'a',label:'設定'},{key:'b',label:'成員'}]" modelValue="a" />`),
          Card('SPagination', `<SPagination :total="100" :pageSize="10" :modelValue="3" />`),
          Card('SSegmented',  `<SSegmented :options="[{label:'日',value:'d'},{label:'月',value:'m'}]" modelValue="d" />`),
          Card('SListItem',   `<SListItem title="設定" description="一般偏好" />`),
          Card('SToolbar',    `<SToolbar><template #left>左側</template><template #right>右側</template></SToolbar>`),
          Card('SSidebarSection', `<SSidebarSection label="工作區" />`),
        ].join(''))}

        ${Section('Overlay & Action', [
          Card('SButton',     `<SButton>Primary</SButton> <SButton variant="ghost">Ghost</SButton>`),
          Card('SIconButton', `<SIconButton><SIcon name="settings" /></SIconButton>`),
          Card('STooltip',    `<STooltip content="這是提示"><SButton size="sm">hover</SButton></STooltip>`),
          Card('SDropdown',   `<SDropdown :items="[{label:'編輯',value:'e'},{label:'刪除',value:'d'}]"><SButton size="sm">…</SButton></SDropdown>`),
          Card('SModal',      `<span class="text-xs text-fg-tertiary">trigger via show=true</span>`),
          Card('SDrawer',     `<span class="text-xs text-fg-tertiary">trigger via show=true</span>`),
        ].join(''))}

        ${Section('Data', [
          Card('STable',     `<STable :columns="[{key:'name',title:'名稱'},{key:'age',title:'年齡'}]" :data="[{name:'A',age:1},{name:'B',age:2}]" />`),
          Card('SCodeBlock', `<SCodeBlock code="console.log('hello')" lang="ts" />`),
        ].join(''))}

        ${Section('Icons (SIcon — 44 names)', `
          <div class="col-span-full bg-surface-raised border border-neutral-200 rounded-xl p-5">
            <div class="grid grid-cols-6 md:grid-cols-12 gap-3 text-fg-secondary">
              ${[
                'plus','x','check','search','trash','edit','copy','download','upload','send','refresh',
                'chevron-down','chevron-up','chevron-left','chevron-right','arrow-right','arrow-left',
                'alert-circle','info','check-circle','alert-triangle','menu','more-horizontal','more-vertical',
                'settings','user','log-out','file-text','folder','message-square','database','loader',
                'external-link','book-open','eye','eye-off','lock','mail','key','share-2','play','pause',
                'filter','sun','moon',
              ].map(n => `
                <div class="flex flex-col items-center gap-1 p-2 hover:bg-neutral-50 rounded-md transition cursor-default">
                  <SIcon name="${n}" :size="20" />
                  <span class="text-[10px] text-fg-tertiary">${n}</span>
                </div>`).join('')}
            </div>
          </div>`)}

      </div>`,
  }),
}
