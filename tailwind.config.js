/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/**/*.js"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#EBF5FF',
          100: '#E1EFFE',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
        },
        gray: {
          50: '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827',
        },
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
