/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './content/**/*.{md,mdx}',
  ],
  theme: {
    extend: {
      // No left-stripe accents (owner decision 2026-11-15): Typography's blockquote draws a 0.25rem inline-start rule.
      // A quote is a light tinted block instead.
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            blockquote: {
              borderInlineStartWidth: '0',
              borderLeftWidth: '0',
              backgroundColor: theme('colors.gray.50'),
              borderRadius: theme('borderRadius.md'),
              paddingInlineStart: '1em',
              paddingInlineEnd: '1em',
              paddingTop: '0.25em',
              paddingBottom: '0.25em',
            },
          },
        },
      }),
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
