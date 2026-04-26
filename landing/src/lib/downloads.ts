/**
 * Hermes installer URLs.
 *
 * Files are published as GitHub Releases by `.github/workflows/release.yml`.
 * The `releases/latest/download/<file>` path is a GitHub-hosted redirect
 * that always serves the most recent release — no need to bump these URLs
 * for every version (the CI uploads stable-named copies alongside the
 * versioned ones).
 *
 * If there are no releases yet, these URLs return 404. The first time you
 * tag `v1.0.0` and the workflow finishes — they start working.
 */

const REPO = "artsignstudiokz/Hermes";

export interface DownloadInfo {
  url: string | null;
  icon: string;
  label: string;
  ext: string;
  size: string;
}

export const DOWNLOADS: Record<"windows" | "macos" | "linux", DownloadInfo> = {
  windows: {
    url: `https://github.com/${REPO}/releases/latest/download/Hermes-Setup.exe`,
    icon: "⊞",
    label: "для Windows",
    ext: ".exe",
    size: "~80 МБ",
  },
  macos: {
    url: `https://github.com/${REPO}/releases/latest/download/Hermes.pkg`,
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

export const RELEASES_PAGE = `https://github.com/${REPO}/releases`;
export const HASHES_WIN = `https://github.com/${REPO}/releases/latest/download/SHA256SUMS.txt`;
export const HASHES_MAC = `https://github.com/${REPO}/releases/latest/download/SHA256SUMS-macos.txt`;
