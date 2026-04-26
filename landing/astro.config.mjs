import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import sitemap from "@astrojs/sitemap";
// @astrojs/vercel >= 8 unified the static + serverless adapters into a single import.
import vercel from "@astrojs/vercel";

const SITE = process.env.PUBLIC_SITE_URL ?? "https://hermes.baicore.kz";

// https://astro.build/config
export default defineConfig({
  site: SITE,
  output: "static",
  adapter: vercel({
    webAnalytics: { enabled: true },
    imageService: true,
  }),
  integrations: [
    tailwind({ applyBaseStyles: false }),
    sitemap(),
  ],
  build: { inlineStylesheets: "auto" },
  prefetch: { defaultStrategy: "viewport" },
  compressHTML: true,
});
