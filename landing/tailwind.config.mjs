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
        marble:    "#FBF7EC",
        ivory:     "#F4ECD8",
        parchment: "#EFE5C8",
        alabaster: "#FAF6EC",
        gold:      "#C9A96E",
        "gold-deep": "#A8884F",
        "gold-light": "#E5CB91",
        bronze:    "#8B6F3E",
        olive:     "#6B7C4F",
        laurel:    "#7E8B5A",
        wine:      "#7A1B27",
        aegean:    "#2E4F6F",
        ink:       "#2A2520",
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
              "0 0 0 1px rgba(201, 169, 110, 0.18), 0 0 36px -4px rgba(201, 169, 110, 0.4)",
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
