import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      backgroundImage: {
        app: "linear-gradient(135deg, #03130f 0%, #06111d 38%, #160a22 72%, #05070f 100%)",
      },
      colors: {
        brand: {
          50: "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
          950: "#052e16",
        },
        lagoon: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
        },
        pulse: {
          300: "#f0abfc",
          400: "#e879f9",
          500: "#d946ef",
        },
      },
      boxShadow: {
        soft: "0 18px 60px rgba(0, 0, 0, 0.32)",
        glow: "0 22px 80px rgba(34, 197, 94, 0.24)",
        slime: "0 18px 70px rgba(34, 197, 94, 0.18), 0 0 0 1px rgba(255, 255, 255, 0.06)",
      },
      borderRadius: {
        fluid: "2rem",
      },
      keyframes: {
        floaty: {
          "0%, 100%": { transform: "translateY(0) scale(1)" },
          "50%": { transform: "translateY(-6px) scale(1.02)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "200% 50%" },
        },
      },
      animation: {
        floaty: "floaty 5s ease-in-out infinite",
        shimmer: "shimmer 7s linear infinite",
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "none",
            code: {
              backgroundColor: "#1e1e2e",
              padding: "0.2em 0.4em",
              borderRadius: "4px",
              fontSize: "0.875em",
            },
          },
        },
      },
    },
  },
  plugins: [],
};

export default config;
