import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#04060a",
        bar: "#070b11",
        panel: "#090d14",
        edge: "#141b27",
        rowdiv: "#0f141d",
        body: "#c9d1d9",
        strong: "#e6edf3",
        muted: "#6e7681",
        muted2: "#5c636d",
        accent: "#2dd4bf",
        up: "#3fb950",
        down: "#f85149",
        warn: "#d29922",
        info: "#58a6ff",
        info2: "#9bbce8",
        violet: "#a78bfa",
      },
      fontFamily: {
        mono: ["'SF Mono'", "Consolas", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
