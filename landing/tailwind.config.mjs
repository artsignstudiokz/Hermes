/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,ts,tsx,md,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["Cormorant Garamond", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        // Sharper palette — ~6% contrast between bg and card so the
        // marble cards stop bleeding into the parchment background, and
        // a deeper gold gradient (royal yellow → muted amber) for the
        // luxury/premium feel.
        marble:    "#F1E9D2",
        ivory:     "#FFFCF1",
        parchment: "#E8DEC0",
        alabaster: "#FFFCF1",
        gold:      "#D4AF37",
        "gold-deep": "#9B7B2D",
        "gold-light": "#F4D783",
        bronze:    "#7A5A1E",
        olive:     "#6B7C4F",
        laurel:    "#5B7A3E",
        wine:      "#8B2C2C",
        aegean:    "#234A6A",
        ink:       "#1A150F",
        "ink-2":   "#4F4536",
        "ink-3":   "#6E6450",
        "ink-4":   "#8A7E66",
      },
      animation: {
        "wing-flutter": "wing-flutter 2.8s ease-in-out infinite",
        "ring-pulse": "ring-pulse 6s ease-in-out infinite",
        "coin-spin": "coin-spin 9s ease-in-out infinite",
        "coin-drift": "coin-drift 7s ease-in-out infinite",
        "float-glyph": "float-glyph 5s ease-in-out infinite",
      },
      keyframes: {
        "wing-flutter": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-3px)" },
        },
        "ring-pulse": {
          "0%, 100%": { opacity: "0.6" },
          "50%": {
            opacity: "0.95",
            boxShadow:
              "0 0 0 1px rgba(155, 123, 45, 0.22), 0 0 40px -4px rgba(212, 175, 55, 0.45)",
          },
        },
        "coin-spin": {
          "0%, 100%": { transform: "rotateY(0deg) rotateX(2deg)" },
          "50%": { transform: "rotateY(18deg) rotateX(-2deg)" },
        },
        "coin-drift": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        "float-glyph": {
          "0%, 100%": { transform: "translateY(0)", opacity: "0.55" },
          "50%": { transform: "translateY(-8px)", opacity: "0.95" },
        },
      },
    },
  },
};
