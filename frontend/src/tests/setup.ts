/**
 * Vitest setup — DOM stubs + matchMedia polyfill (jsdom doesn't ship it).
 */

import "@testing-library/jest-dom/vitest";

// matchMedia polyfill (used by ThemeProvider).
if (typeof window !== "undefined" && !window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// IntersectionObserver polyfill — used by scroll-reveal effects.
if (typeof window !== "undefined" && !("IntersectionObserver" in window)) {
  // @ts-expect-error — minimal stub for tests
  window.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() { return []; }
  };
}
