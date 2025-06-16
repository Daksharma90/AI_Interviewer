/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        inter: ['Inter', 'sans-serif'],
      },
      colors: {
        primary: '#3B82F6', // Blue-500
        secondary: '#60A5FA', // Blue-400
        accent: '#10B981', // Emerald-500
        background: '#F3F4F6', // Gray-100
        text: '#1F2937', // Gray-900
      },
    },
  },
  plugins: [],
}
