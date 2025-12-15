import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#e6f0ff",
          100: "#cce0ff",
          200: "#99c2ff",
          300: "#66a3ff",
          400: "#3385ff",
          500: "#005eff",
          600: "#004ecc",
          700: "#003d99",
          800: "#142357",
          900: "#0f1a40",
        },
        accent: {
          50: "#f0f4ff",
          100: "#e0e8ff",
          200: "#c2d1ff",
          300: "#99b3ff",
          400: "#6690ff",
          500: "#3366ff",
          600: "#2952cc",
          700: "#1f3d99",
          800: "#142357",
          900: "#0d1733",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
