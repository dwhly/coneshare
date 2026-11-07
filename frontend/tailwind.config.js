/** @type {import('tailwindcss').Config} */
// Fleet design system (vendored preset, see public/fds/README.md). Colours are roles that read tokens.css
// variables, so light/dark ([data-theme], the preset's darkMode selector) and density ([data-density])
// come from the CSS layer. Raw Tailwind palette classes are not used: see
// scripts/fds-codemod.py and `check-literals.py src` (must report 0).
export default {
  presets: [require("./fds.preset.cjs")],
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Selected state (active segment, chosen row): NEUTRAL role, never brand or status (DESIGN.md §6).
        selected: {
          DEFAULT: "hsl(var(--selected) / <alpha-value>)",
          foreground: "hsl(var(--selected-foreground) / <alpha-value>)",
          border: "hsl(var(--selected-border) / <alpha-value>)",
        },
      },
      borderRadius: {
        // Controls (buttons, inputs, tabs, pills) are "in between" round: --radius-control (6px, DESIGN.md §7).
        // Cards keep `rounded-lg` = --radius (density-driven).
        md: "var(--radius-control)",
        sm: "calc(var(--radius-control) * 0.75)",
        control: "var(--radius-control)",
        pill: "calc(var(--radius-control) * 0.75)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    require("@tailwindcss/typography"),
  ],
};
