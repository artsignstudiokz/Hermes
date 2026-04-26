/**
 * Hermes — Greek-mythology design tokens.
 * Product is "Hermes" (god of trade); developer is BAI Core.
 * Aesthetic: marble + classical gold + olive + deep wine. Light theme by default.
 */

export const brand = {
  // Product
  name: "Hermes",
  productFull: "Hermes — Trading Bot",
  tagline: "Бог торговли. Ваш бот.",
  subtitle: "Профессиональная автоматическая торговля",
  // Developer (separate from product)
  developer: "BAI Core",
  developerUrl: "https://baicore.kz",
  developerEmail: "info@baicore.kz",
  // Mythology
  godName: "Ἑρμῆς",          // Greek spelling
  godNameLatin: "Hermes",
  caduceusGlyph: "☤",         // unicode caduceus
} as const;

/** Color palette inspired by classical antiquity. */
export const palette = {
  // Backgrounds — marble, parchment, fresco
  marble: "#FBF7EC",
  ivory: "#F4ECD8",
  parchment: "#EFE5C8",
  alabaster: "#FAF6EC",
  // Accents — gold, bronze, olive
  gold: "#C9A96E",
  goldDeep: "#A8884F",
  goldLight: "#E5CB91",
  bronze: "#8B6F3E",
  olive: "#6B7C4F",
  laurel: "#7E8B5A",
  // Contrast — wine, navy, ink
  wine: "#7A1B27",
  aegean: "#2E4F6F",         // deep Mediterranean blue
  ink: "#2A2520",
  // Status
  success: "#5B7B4A",
  danger: "#A8332E",
  warning: "#C77E2E",
} as const;

export const motion = {
  fast: 0.15,
  base: 0.25,
  slow: 0.4,
  spring: { type: "spring", stiffness: 260, damping: 28 } as const,
} as const;

export const layout = {
  titleBarHeight: 40,
  sidebarWidth: 256,
  sidebarCollapsedWidth: 72,
  bottomNavHeight: 64,
} as const;
