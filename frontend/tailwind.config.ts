import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f8fbff",
        ink: "#07182f",
        midnight: "#021a35",
        midnightSoft: "#08284f",
        snow: "#f8fbff",
        ice: "#edf6fb",
        powder: "#dbeaf5",
        line: "#cbd9e8",
        muted: "#53657d",
        alpenglow: "#ff5f8f",
        alpenglowSoft: "#ffe1eb",
        alpineBlue: "#0b5fb8",
        pine: "#087f68",
        amber: "#f59e0b",
        warning: "#f15a24",
        ember: "#d6673f",
        alpine: "#2f645c",
        frost: "#dce8ef",
      },
      boxShadow: {
        panel: "0 20px 50px rgba(24, 34, 47, 0.12)",
        premium: "0 24px 80px rgba(2, 26, 53, 0.18)",
      },
      fontFamily: {
        display: ["'Sora'", "ui-sans-serif", "system-ui"],
        body: ["'Manrope'", "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
} satisfies Config;
