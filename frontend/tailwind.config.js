/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: '#1A1AFF',
        cyan: '#00F5FF',
        violet: '#7C4DFF',
        amber: '#FFB300',
        green: '#00E676',
        red: '#FF3B30',
        bg: '#0D0D0D',
        surface: '#1C1C1E',
        surface2: '#242428',
        surface3: '#2E2E34',
      },
      fontFamily: {
        exo: ['"Exo 2"', 'sans-serif'],
        rajdhani: ['Rajdhani', 'sans-serif'],
        mono: ['"Space Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}
