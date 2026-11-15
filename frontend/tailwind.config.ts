import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#080b0f",
          900: "#0d1117",
          800: "#131a22",
          700: "#1b242e",
          600: "#26323f",
          500: "#384858",
          400: "#5a6b7c",
        },
        paper: {
          DEFAULT: "#e8e0cd",
          dim: "#b9b09c",
          faint: "#7d776a",
        },
        vermilion: {
          DEFAULT: "#c8492f",
          bright: "#e05a3c",
          deep: "#8f2f1d",
        },
        jade: "#5c8a76",
        gold: "#b08a4a",
      },
      fontFamily: {
        display: [
          "Noto Serif SC",
          "Source Han Serif SC",
          "Songti SC",
          "SimSun",
          "STSong",
          "serif",
        ],
        sans: [
          "Inter",
          "PingFang SC",
          "Microsoft YaHei",
          "Noto Sans SC",
          "system-ui",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Cascadia Code", "Consolas", "monospace"],
      },
      boxShadow: {
        panel: "0 32px 80px -24px rgba(0, 0, 0, 0.85)",
        seal: "0 0 0 1px rgba(200, 73, 47, 0.35), 0 8px 32px -8px rgba(200, 73, 47, 0.45)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "48px 48px",
      },
      transitionTimingFunction: {
        archive: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;
