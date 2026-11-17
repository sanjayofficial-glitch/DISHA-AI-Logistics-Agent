/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        disha: {
          50: "#fff8ed",
          100: "#ffefd4",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
        },
        navy: {
          950: "#0a1628",
          900: "#0f1f38",
          800: "#16294a",
          700: "#1e355f",
          600: "#274377",
          500: "#33548f",
          200: "#b9cdea",
          100: "#dce6f5",
        },
      },
    },
  },
  plugins: [],
};
