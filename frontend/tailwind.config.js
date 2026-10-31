/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#FF2E55',
          50: '#FFF0F3',
          100: '#FFE1E7',
          200: '#FFC4D0',
          300: '#FF94A8',
          400: '#FF5C7E',
          500: '#FF2E55',
          600: '#E6153E',
          700: '#C20A2F',
          800: '#A10D2C',
          900: '#86102B',
          950: '#4A0313',
        },
        darkSurface: '#0F0F12',
        darkSurfaceSubtle: '#18181D',
        darkSurfaceBorder: '#272730',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'Monaco', 'Consolas', '"Liberation Mono"', '"Courier New"', 'monospace'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      keyframes: {
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.8', boxShadow: '0 0 15px rgba(255, 46, 85, 0.4)' },
          '50%': { opacity: '1', boxShadow: '0 0 25px rgba(255, 46, 85, 0.8)' },
        },
        scanLine: {
          '0%': { top: '0%' },
          '100%': { top: '100%' },
        }
      },
      animation: {
        marquee: 'marquee 30s linear infinite',
        pulseGlow: 'pulseGlow 2s ease-in-out infinite',
        scanLine: 'scanLine 3s linear infinite',
      }
    },
  },
  plugins: [],
}
