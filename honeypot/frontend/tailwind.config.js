/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0a", // deeply dark
        surface: "#111111", 
        primary: "#10b981",    // Emerald Green (Cybersecurity)
        secondary: "#3b82f6",  // Blue (Trust)
        danger: "#ef4444",     // Red (Scam)
        text: {
          primary: "#ededed",
          secondary: "#a1a1aa",
        },
        glass: {
          100: "rgba(255, 255, 255, 0.05)",
          200: "rgba(255, 255, 255, 0.1)",
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
