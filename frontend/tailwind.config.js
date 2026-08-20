/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        governor: {
          50: "#f0fdf4",
          100: "#dcfce7",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
          950: "#052e16"
        },
        cyber: {
          slate: "#0f172a",
          card: "#1e293b",
          border: "#334155",
          accent: "#38bdf8",
          denied: "#f43f5e",
          allowed: "#10b981",
          warning: "#f59e0b"
        }
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Fira Code'", "monospace"],
        sans: ["'Inter'", "system-ui", "sans-serif"]
      }
    },
  },
  plugins: [],
}
