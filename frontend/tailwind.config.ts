import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f4efe7",
        ink: "#18222f",
        ember: "#d6673f",
        alpine: "#2f645c",
        frost: "#dce8ef",
      },
      boxShadow: {
        panel: "0 20px 50px rgba(24, 34, 47, 0.12)",
      },
      fontFamily: {
        display: ["'Sora'", "ui-sans-serif", "system-ui"],
        body: ["'Manrope'", "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
} satisfies Config;
