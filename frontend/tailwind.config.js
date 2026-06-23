/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Instrument Serif', 'serif'],
      },
      colors: {
        ink: {
          DEFAULT: '#1a1a1a',
          muted: '#6b6258',
          faint: '#a39888',
        },
        paper: {
          DEFAULT: '#faf8f3',
          deep: '#f0ebe0',
          bg: '#f8f7f4',
        },
        accent: '#8b1e1e',
        ok: '#2d5016',
        warn: '#8a5a00',
      },
    },
  },
  plugins: [],
};
