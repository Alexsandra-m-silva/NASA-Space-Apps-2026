import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        sand: "var(--sand-deep)",
        olive: "var(--olive-ink)",
        signal: {
          DEFAULT: "var(--signal)",
          soft: "var(--signal-soft)",
        },
        earth: "var(--warn-earth)",
        brand: {
          cafe: "var(--cafe)",
          barro: "var(--barro)",
          sol: "var(--sol)",
          ocre: "var(--ocre)",
          mel: "var(--mel)",
          /* Legacy aliases → Terra e luz */
          floresta: "var(--cafe)",
          conexao: "var(--barro)",
          broto: "var(--sol)",
          terra: "var(--ocre)",
          areia: "var(--areia)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        info: "var(--info)",
        chart: {
          "1": "var(--chart-1)",
          "2": "var(--chart-2)",
          "3": "var(--chart-3)",
          "4": "var(--chart-4)",
          "5": "var(--chart-5)",
        },
        seq: {
          "1": "var(--seq-1)",
          "2": "var(--seq-2)",
          "3": "var(--seq-3)",
          "4": "var(--seq-4)",
          "5": "var(--seq-5)",
        },
        div: {
          low: "var(--div-low)",
          "low-mid": "var(--div-low-mid)",
          mid: "var(--div-mid)",
          "high-mid": "var(--div-high-mid)",
          high: "var(--div-high)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
