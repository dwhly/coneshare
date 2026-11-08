/* fleet-design-system — Tailwind v3.4 preset.
   Colours resolve to tokens.css variables, so light/dark, brand and density
   come from the CSS layer; this preset never changes for a re-brand. */
const { fontFamily } = require('tailwindcss/defaultTheme');

const hsl = (v) => `hsl(var(--${v}) / <alpha-value>)`;
const status = (n) => ({
  DEFAULT: hsl(n), foreground: hsl(`${n}-foreground`), subtle: hsl(`${n}-subtle`), border: hsl(`${n}-border`),
});
const scale = (p) => Object.fromEntries(
  [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950].map((s) => [s, hsl(`${p}-${s}`)]));
const tags = Object.fromEntries([1, 2, 3, 4, 5, 6].map((i) => [i, { DEFAULT: hsl(`tag-${i}`), subtle: hsl(`tag-${i}-subtle`) }]));

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: hsl('canvas'),
        border: hsl('border'),
        input: hsl('input'),
        ring: hsl('ring'),
        background: hsl('background'),
        foreground: hsl('foreground'),
        primary: { DEFAULT: hsl('primary'), foreground: hsl('primary-foreground') },
        secondary: { DEFAULT: hsl('secondary'), foreground: hsl('secondary-foreground') },
        muted: { DEFAULT: hsl('muted'), foreground: hsl('muted-foreground') },
        accent: { DEFAULT: hsl('accent'), foreground: hsl('accent-foreground') },
        popover: { DEFAULT: hsl('popover'), foreground: hsl('popover-foreground') },
        card: { DEFAULT: hsl('card'), foreground: hsl('card-foreground') },
        destructive: { DEFAULT: hsl('destructive'), foreground: hsl('destructive-foreground') },
        danger: status('danger'),
        warning: status('warning'),
        success: status('success'),
        info: status('info'),
        neutral: status('neutral'),
        tag: tags,
        brand: {
          DEFAULT: hsl('brand'),
          foreground: hsl('brand-foreground'),
          subtle: hsl('brand-subtle'),
          muted: hsl('brand-muted'),
          'muted-foreground': hsl('brand-muted-foreground'),
        },
        gray: scale('gray'),
      },
      fontFamily: {
        sans: ['var(--font-sans)', ...fontFamily.sans],
        display: ['var(--font-display)', ...fontFamily.sans],
        mono: ['var(--font-mono)', ...fontFamily.mono],
      },
      fontSize: { base: 'var(--text-base)' },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      spacing: { row: 'var(--row-pad-y)', card: 'var(--card-pad)', gap: 'var(--gap)' },
      height: { shell: 'var(--shell-height)' },
    },
  },
};
