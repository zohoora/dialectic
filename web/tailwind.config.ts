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
        // Mission Control palette
        void: {
          DEFAULT: "#0a0e14",
          50: "#0d1219",
          100: "#111820",
          200: "#151d27",
          300: "#1a232e",
          400: "#1f2937",
        },
        slate: {
          750: "#293548",
          850: "#172033",
        },
        // Agent role colors
        agent: {
          advocate: "#22c55e",
          empiricist: "#3b82f6",
          mechanist: "#a855f7",
          skeptic: "#ef4444",
          patient: "#f59e0b",
          arbitrator: "#06b6d4",
        },
        // Accent colors
        accent: {
          primary: "#22d3ee",
          secondary: "#818cf8",
          success: "#34d399",
          warning: "#fbbf24",
          danger: "#f87171",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      backgroundImage: {
        "grid-pattern": `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.02'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        "gradient-radial": "radial-gradient(ellipse at center, var(--tw-gradient-stops))",
        "glow-cyan": "radial-gradient(ellipse at center, rgba(34, 211, 238, 0.15) 0%, transparent 70%)",
        "glow-purple": "radial-gradient(ellipse at center, rgba(168, 85, 247, 0.15) 0%, transparent 70%)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow": "spin 8s linear infinite",
        "float": "float 6s ease-in-out infinite",
        "typing": "typing 1.5s steps(3) infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
        "slide-up": "slideUp 0.3s ease-out",
        "slide-down": "slideDown 0.3s ease-out",
        "fade-in": "fadeIn 0.4s ease-out",
        "scale-in": "scaleIn 0.2s ease-out",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        typing: {
          "0%": { opacity: "0.2" },
          "50%": { opacity: "1" },
          "100%": { opacity: "0.2" },
        },
        glow: {
          "0%": { boxShadow: "0 0 5px rgba(34, 211, 238, 0.5), 0 0 10px rgba(34, 211, 238, 0.3)" },
          "100%": { boxShadow: "0 0 10px rgba(34, 211, 238, 0.8), 0 0 20px rgba(34, 211, 238, 0.5)" },
        },
        slideUp: {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideDown: {
          "0%": { transform: "translateY(-10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        scaleIn: {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },
      boxShadow: {
        "glow-sm": "0 0 10px rgba(34, 211, 238, 0.3)",
        "glow-md": "0 0 20px rgba(34, 211, 238, 0.4)",
        "glow-lg": "0 0 30px rgba(34, 211, 238, 0.5)",
        "inner-glow": "inset 0 0 20px rgba(34, 211, 238, 0.1)",
        "glass": "0 8px 32px rgba(0, 0, 0, 0.3)",
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};

export default config;

