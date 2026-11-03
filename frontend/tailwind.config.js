/** @type {import('tailwindcss').Config} */
export default {
  presets: [require("./amforge.preset.cjs")],
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // AmForge: semantic colours, radius, fonts and the tokenised `gray` scale come from the preset.
      // `indigo` (Coneshare's link/focus accent) aliases the AmForge brand scale.
      colors: {
        indigo: Object.fromEntries(
          [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950].map((n) => [n, `hsl(var(--af-brand-${n}) / <alpha-value>)`])
        ),
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
