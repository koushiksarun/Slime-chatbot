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
        app: "linear-gradient(180deg, #030712 0%, #020617 52%, #050816 100%)",
      },
      colors: {
        brand: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          900: "#0c4a6e",
        },
      },
      boxShadow: {
        soft: "0 18px 60px rgba(0, 0, 0, 0.28)",
        glow: "0 20px 70px rgba(14, 165, 233, 0.22)",
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
