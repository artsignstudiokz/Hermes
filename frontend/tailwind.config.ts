import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * Hermes — Greek-mythology design system.
 * Light theme by default (marble + gold). Dark mode optional.
 */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.25rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        // Hermes brand palette (navy + gold from the official logo)
        hermes: {
          marble: "#FBF7EC",
          ivory: "#F4ECD8",
          parchment: "#EFE5C8",
          alabaster: "#FAF6EC",
          gold: "#C9A96E",
          "gold-deep": "#A8884F",
          "gold-light": "#E5CB91",
          bronze: "#8B6F3E",
          olive: "#6B7C4F",
          laurel: "#7E8B5A",
          wine: "#7A1B27",
          aegean: "#2E4F6F",
          navy: "#1B2940",          // logo wordmark + helmet
          "navy-deep": "#11192A",
          "navy-soft": "#2C3D5C",
          ink: "#2A2520",
        },
      },
      borderRadius: {
        sm: "calc(var(--radius) - 4px)",
        md: "calc(var(--radius) - 2px)",
        lg: "var(--radius)",
        xl: "calc(var(--radius) + 4px)",
      },
      fontFamily: {
        // Body / UI
        sans: [
          "Inter",
          "ui-sans-serif",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        // Display / classical
        serif: [
          "Cormorant Garamond",
          "Playfair Display",
          "Cormorant",
          "Georgia",
          "serif",
        ],
        // Numbers / tickers
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      backgroundImage: {
        "marble-grain":
          "radial-gradient(circle at 20% 0%, rgba(201,169,110,0.10) 0%, transparent 50%), radial-gradient(circle at 80% 100%, rgba(123,138,90,0.07) 0%, transparent 55%), linear-gradient(180deg, #FBF7EC 0%, #F4ECD8 100%)",
        "gold-shine":
          "linear-gradient(135deg, #E5CB91 0%, #C9A96E 50%, #A8884F 100%)",
        "laurel-stripe":
          "repeating-linear-gradient(45deg, rgba(123,138,90,0.04) 0px, rgba(123,138,90,0.04) 8px, transparent 8px, transparent 16px)",
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.6) inset, 0 12px 32px -16px rgba(42,37,32,0.18)",
        gold: "0 0 0 1px rgba(201,169,110,0.4), 0 8px 24px -8px rgba(168,136,79,0.45)",
        marble: "0 24px 56px -28px rgba(42,37,32,0.25), 0 4px 16px -8px rgba(42,37,32,0.12)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "gold-pulse": {
          "0%, 100%": { opacity: "0.7", filter: "brightness(1)" },
          "50%": { opacity: "1", filter: "brightness(1.15)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "wing-flutter": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-3px)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "gold-pulse": "gold-pulse 2.6s ease-in-out infinite",
        shimmer: "shimmer 3s linear infinite",
        "wing-flutter": "wing-flutter 2.8s ease-in-out infinite",
      },
    },
  },
  plugins: [animate],
} satisfies Config;
