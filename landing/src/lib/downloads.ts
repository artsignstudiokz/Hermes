/**
 * Hermes installer URLs. Update once CI publishes binaries.
 * Files are expected at /releases/<name> on the production domain
 * (Vercel will route static files automatically).
 */

export interface DownloadInfo {
  url: string | null;
  icon: string;
  label: string;
  ext: string;
  size: string;
}

export const DOWNLOADS: Record<"windows" | "macos" | "linux", DownloadInfo> = {
  windows: {
    url: "/releases/Hermes-Setup-1.0.0.exe",
    icon: "⊞",
    label: "для Windows",
    ext: ".exe",
    size: "~80 МБ",
  },
  macos: {
    url: "/releases/Hermes-1.0.0.pkg",
    icon: "",
    label: "для macOS",
    ext: ".pkg",
    size: "~85 МБ",
  },
  linux: {
    url: null,
    icon: "🐧",
    label: "для Linux (скоро)",
    ext: ".AppImage",
    size: "—",
  },
};

export type OSId = keyof typeof DOWNLOADS;
