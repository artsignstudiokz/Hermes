import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      strategies: "generateSW",
      includeAssets: [
        "hermes-emblem.svg",
        "meander.svg",
        "baicore-logo.svg",
        "favicon.svg",
      ],
      manifest: {
        name: "Hermes — Trading Bot",
        short_name: "Hermes",
        description: "Бог торговли. Ваш бот. Разработано BAI Core.",
        theme_color: "#FBF7EC",
        background_color: "#FBF7EC",
        display: "standalone",
        orientation: "any",
        start_url: "/",
        lang: "ru",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icons/icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Don't cache /api/* — always go to network. PWA shell only.
        navigateFallbackDenylist: [/^\/api\//, /^\/ws\//],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
            handler: "NetworkOnly",
          },
        ],
        // Inject our push event handler into the generated SW.
        importScripts: ["/service-worker-push.js"],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://127.0.0.1:8765",
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: mode !== "production",
    target: "es2022",
  },
}));
