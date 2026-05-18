/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,js}'],
  theme: {
    extend: {
      colors: {
        // 對齊 apps/web 的 brand 階層（簡化版）
        brand: {
          50: '#eef4ff',
          100: '#dbe6ff',
          500: '#3b6ee8',
          600: '#2e57c5',
          700: '#264aa3',
          900: '#16306b',
        },
        ink: {
          900: '#0f172a',
          700: '#334155',
          500: '#64748b',
          300: '#cbd5e1',
          100: '#f1f5f9',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Noto Sans TC"',
          '"PingFang TC"',
          'sans-serif',
        ],
      },
      maxWidth: {
        content: '1180px',
      },
    },
  },
  plugins: [],
}
