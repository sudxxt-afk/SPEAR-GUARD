/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'danger-orange': '#ff6b35',
        'dark-gray': '#1a1a1a',
        'mid-gray': '#2d2d2d',
        'light-gray': '#4a4a4a',
      },
    },
  },
  plugins: [],
};
