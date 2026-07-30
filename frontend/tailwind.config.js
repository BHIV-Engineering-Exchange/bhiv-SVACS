/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          0: "#070a0d",
          1: "#0b1014",
          2: "#11171d",
          3: "#161e26",
        },
        line: {
          DEFAULT: "#1c2530",
          strong: "#26323f",
        },
        fg: {
          0: "#e6edf3",
          1: "#9aa7b2",
          2: "#5e6b76",
          3: "#3a4651",
        },
        ok: "#22c55e",
        warn: "#f59e0b",
        err: "#ef4444",
        info: "#38bdf8",
        accent: {
          cyan: "#22d3ee",
          violet: "#a78bfa",
          green: "#4ade80",
          amber: "#fbbf24",
          rose: "#fb7185",
        },
        stage: {
          signal: "#22d3ee",
          perception: "#4ade80",
          intelligence: "#a78bfa",
          state: "#fbbf24",
          bucket: "#38bdf8",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.02) inset, 0 0 0 1px rgba(255,255,255,0.02)",
        glow: "0 0 24px -6px var(--tw-shadow-color)",
      },
      animation: {
        "pulse-soft": "pulseSoft 2.4s ease-in-out infinite",
        "pulse-fast": "pulseSoft 1.2s ease-in-out infinite",
        flow: "flow 2s linear infinite",
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
        flow: {
          "0%": { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "100% 0%" },
        },
      },
    },
  },
  plugins: [],
};
