// VENDORED from amforge-deal-suite/packages/amforge-ui/tailwind.preset.cjs — edit there, then run scripts/sync.sh
/**
 * AmForge Tailwind preset (Tailwind CSS v3.4) — consumed by Send (Coneshare frontend) and Sign
 * (Documenso packages/tailwind-config). Every value resolves to a CSS variable from tokens.css, so
 * the preset never needs to change for a re-brand: edit tokens.css instead.
 *
 * Usage (both apps):   module.exports = { presets: [require('./amforge.preset.cjs')], ... }
 * App configs are applied AFTER presets, so an app may still extend/override any key.
 */
const { fontFamily } = require('tailwindcss/defaultTheme');

const hsl = (name) => `hsl(var(--${name}) / <alpha-value>)`;

const scale = (prefix) =>
  Object.fromEntries(
    [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950].map((step) => [step, hsl(`${prefix}-${step}`)]),
  );

/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        // shadcn semantic tokens (1:1 with Documenso + Coneshare component layers)
        border: hsl('border'),
        input: hsl('input'),
        ring: hsl('ring'),
        background: hsl('background'),
        foreground: hsl('foreground'),
        primary: { DEFAULT: hsl('primary'), foreground: hsl('primary-foreground') },
        secondary: { DEFAULT: hsl('secondary'), foreground: hsl('secondary-foreground') },
        destructive: { DEFAULT: hsl('destructive'), foreground: hsl('destructive-foreground') },
        muted: { DEFAULT: hsl('muted'), foreground: hsl('muted-foreground') },
        accent: { DEFAULT: hsl('accent'), foreground: hsl('accent-foreground') },
        popover: { DEFAULT: hsl('popover'), foreground: hsl('popover-foreground') },
        card: { DEFAULT: hsl('card'), foreground: hsl('card-foreground') },
        success: { DEFAULT: hsl('success') },
        warning: { DEFAULT: hsl('warning') },

        // AmForge brand accent (single accent colour) + full scale for tints
        brand: {
          DEFAULT: hsl('brand'),
          foreground: hsl('brand-foreground'),
          muted: hsl('brand-muted'),
          'muted-foreground': hsl('brand-muted-foreground'),
          ...scale('af-brand'),
        },

        // Neutral scale is tokenised too: every literal `bg-gray-900` / `text-gray-500` in either app
        // now follows --af-gray-*. (Coneshare has ~1.5k literal gray utilities; this re-skins them
        // without touching call sites.)
        gray: scale('af-gray'),
      },
      fontFamily: {
        sans: ['var(--font-sans)', ...fontFamily.sans],
        mono: ['var(--font-mono)', ...fontFamily.mono],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      height: {
        shell: 'var(--af-shell-height)',
      },
    },
  },
};
