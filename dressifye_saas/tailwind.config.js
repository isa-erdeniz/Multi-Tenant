/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#fdf2f8",
          500: "#ec4899",
          600: "#db2777",
          700: "#be185d",
        },
        secondary: {
          50: "#f5f3ff",
          500: "#8b5cf6",
          600: "#7c3aed",
        },
        accent: {
          50: "#ecfdf5",
          500: "#10b981",
          600: "#059669",
        },
        brand: {
          black: "#0a0a0a",
          ivory: "#f5f0e8",
          gold: "#c9a84c",
        },
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans", "sans-serif"],
        display: ["Playfair Display", "serif"],
      },
    },
  },
  plugins: [],
};
