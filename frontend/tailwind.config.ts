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
      colors: {
        // Dark glassmorphism palette
        surface: {
          DEFAULT: "rgba(13, 13, 18, 0.95)",
          panel: "rgba(18, 18, 26, 0.90)",
          card: "rgba(24, 24, 36, 0.85)",
          hover: "rgba(30, 30, 44, 0.90)",
        },
        border: {
          DEFAULT: "rgba(255, 255, 255, 0.06)",
          active: "rgba(255, 255, 255, 0.12)",
        },
        accent: {
          DEFAULT: "#6366f1",  // indigo
          hover: "#818cf8",
          muted: "rgba(99, 102, 241, 0.15)",
        },
        confidence: {
          high: "#22c55e",
          medium: "#f59e0b",
          low: "#ef4444",
        },
        text: {
          primary: "rgba(255, 255, 255, 0.95)",
          secondary: "rgba(255, 255, 255, 0.60)",
          muted: "rgba(255, 255, 255, 0.35)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};

export default config;
