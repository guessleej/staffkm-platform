/**
 * @staffkm/design-tokens — Tailwind preset
 *
 * 用法（Tailwind v3）：
 *   // tailwind.config.js
 *   const preset = require('@staffkm/design-tokens/tailwind')
 *   module.exports = { presets: [preset], content: [...] }
 *
 * 同時記得在你的 entry CSS 裡 import：
 *   @import "@staffkm/design-tokens/css";
 */

// 把 CSS variable 轉 hsl()，支援 / opacity 語法
const hsl = (name) => `hsl(var(--color-${name}) / <alpha-value>)`;

const brandScale = (role) => ({
  50:  hsl(`${role}-50`),
  100: hsl(`${role}-100`),
  200: hsl(`${role}-200`),
  300: hsl(`${role}-300`),
  400: hsl(`${role}-400`),
  500: hsl(`${role}-500`),
  600: hsl(`${role}-600`),
  700: hsl(`${role}-700`),
  800: hsl(`${role}-800`),
  900: hsl(`${role}-900`),
  950: hsl(`${role}-950`),
});

const semanticScale = (role) => ({
  50:  hsl(`${role}-50`),
  500: hsl(`${role}-500`),
  600: hsl(`${role}-600`),
  700: hsl(`${role}-700`),
});

module.exports = {
  theme: {
    colors: {
      transparent: 'transparent',
      current:     'currentColor',
      white:       '#ffffff',
      black:       '#000000',

      brand:   brandScale('brand'),
      neutral: brandScale('neutral'),

      success: semanticScale('success'),
      warning: semanticScale('warning'),
      danger:  semanticScale('danger'),
      info:    semanticScale('info'),

      surface: {
        base:    hsl('surface-base'),
        raised:  hsl('surface-raised'),
        overlay: hsl('surface-overlay'),
        sunken:  hsl('surface-sunken'),
      },

      // Tailwind 慣用別名（讓既有 class 不必全改）
      gray:   brandScale('neutral'),
      slate:  brandScale('neutral'),
      indigo: brandScale('brand'),
      rose:   semanticScale('danger'),
      amber:  semanticScale('warning'),
      emerald: semanticScale('success'),
      sky:    semanticScale('info'),
      violet: brandScale('brand'),
    },

    extend: {
      fontFamily: {
        sans:  ['var(--font-sans)'],
        mono:  ['var(--font-mono)'],
        serif: ['var(--font-serif)'],
      },
      borderRadius: {
        sm:   'var(--radius-sm)',
        md:   'var(--radius-md)',
        lg:   'var(--radius-lg)',
        xl:   'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        full: 'var(--radius-full)',
      },
      boxShadow: {
        xs:    'var(--shadow-xs)',
        sm:    'var(--shadow-sm)',
        md:    'var(--shadow-md)',
        lg:    'var(--shadow-lg)',
        xl:    'var(--shadow-xl)',
        '2xl': 'var(--shadow-2xl)',
        inner: 'var(--shadow-inner)',
        focus: 'var(--shadow-focus)',
      },
      transitionDuration: {
        instant: 'var(--duration-instant)',
        fast:    'var(--duration-fast)',
        base:    'var(--duration-base)',
        slow:    'var(--duration-slow)',
      },
      transitionTimingFunction: {
        out:    'var(--ease-out)',
        in:     'var(--ease-in)',
        spring: 'var(--ease-spring)',
      },
      zIndex: {
        dropdown: 'var(--z-dropdown)',
        sticky:   'var(--z-sticky)',
        fixed:    'var(--z-fixed)',
        overlay:  'var(--z-overlay)',
        modal:    'var(--z-modal)',
        popover:  'var(--z-popover)',
        tooltip:  'var(--z-tooltip)',
        toast:    'var(--z-toast)',
      },
    },
  },
  darkMode: ['class', '[data-theme="dark"]'],
};
