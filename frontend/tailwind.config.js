/** Tailwind 只做布局辅助，颜色一律走 styles/tokens.css 的 var()。 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        deep: 'var(--deep)',
        'deep-2': 'var(--deep-2)',
        parch: 'var(--parch)',
        brass: 'var(--brass)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        warn: 'var(--warn)',
      },
      fontFamily: {
        display: ['Marcellus', 'Georgia', 'serif'],
        body: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
