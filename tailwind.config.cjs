/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'solar-yellow': '#E5B84C',
        'solar-yellow-light': '#F5D78C',
        'solar-yellow-dark': '#C99A2E',
        'eco-green': '#5A7A5A',
        'eco-green-light': '#7A9A7A',
        'eco-green-dark': '#3D5A3D',
        'dark': '#1A1A1A',
        'dark-light': '#2D2D2D',
        'dark-lighter': '#3D3D3D',
        'light': '#F8F9FA',
        'light-dark': '#E9ECEF',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
