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
        // Asosiy — ko'k/indigo (redesign: oklch hue ~258)
        primary: {
          50:  "#eef3fc",
          100: "#dde6fa",
          200: "#c2d1f6",
          300: "#9db3f0",
          400: "#6d8bea",
          500: "#3b5bdb",
          600: "#2f49c2",
          700: "#2839a0",
          800: "#243081",
          900: "#20295f",
        },
        // Urg'u — yashil (.uz, narxlar, tasdiqlangan)
        accent: {
          50:  "#e7f7ef",
          100: "#c8efdb",
          200: "#93e0bb",
          300: "#56cd97",
          400: "#22b877",
          500: "#12a65f",
          600: "#0b8c4e",
          700: "#0b7a44",
          800: "#0a6338",
          900: "#084f2d",
        },
      },
      fontFamily: {
        sans: ["var(--font-manrope)", "var(--font-inter)", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
        "card-hover": "0 8px 24px 0 rgb(0 0 0 / 0.09), 0 2px 6px -1px rgb(0 0 0 / 0.06)",
        "card-lg": "0 12px 40px 0 rgb(0 0 0 / 0.10)",
        "nav": "0 1px 0 0 rgb(0 0 0 / 0.06)",
        // Redesign — rangli yumshoq soyalar
        "primary-glow": "0 8px 20px -8px rgb(59 91 219 / 0.55)",
        "float": "0 24px 56px -24px rgb(35 48 129 / 0.28), 0 2px 6px -2px rgb(35 48 129 / 0.08)",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.25s ease-out",
        "scale-in": "scaleIn 0.2s ease-out",
        "shimmer": "shimmer 1.6s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
