/**
 * Hermes installer URLs.
 *
 * Two states:
 *   1. PRE-RELEASE (current) — `comingSoon = true`. Buttons send users to
 *      the GitHub Releases page so they can see "no releases yet" instead
 *      of a 404 from /latest/download.
 *   2. POST-RELEASE — flip `comingSoon = false`. URLs resolve to the
 *      stable-named installers uploaded by .github/workflows/release.yml
 *      (Hermes-Setup.exe on Windows, Hermes.pkg on macOS).
 *
 * Files are published as GitHub Releases by tagging `vX.Y.Z` and pushing.
 */

const REPO = "artsignstudiokz/Hermes";

// Flip to `false` once CI has published the first installer build.
const COMING_SOON = true;

const RELEASES = `https://github.com/${REPO}/releases`;

export interface DownloadInfo {
  url: string | null;
  icon: string;
  label: string;
  ext: string;
  size: string;
  pending?: boolean;
}

export const DOWNLOADS: Record<"windows" | "macos" | "linux", DownloadInfo> = {
  windows: {
    url: COMING_SOON ? RELEASES : `https://github.com/${REPO}/releases/latest/download/Hermes-Setup.exe`,
    icon: "⊞",
    label: COMING_SOON ? "для Windows · скоро" : "для Windows",
    ext: ".exe",
    size: COMING_SOON ? "—" : "~80 МБ",
    pending: COMING_SOON,
  },
  macos: {
    url: COMING_SOON ? RELEASES : `https://github.com/${REPO}/releases/latest/download/Hermes.pkg`,
    icon: "",
    label: COMING_SOON ? "для macOS · скоро" : "для macOS",
    ext: ".pkg",
    size: COMING_SOON ? "—" : "~85 МБ",
    pending: COMING_SOON,
  },
  linux: {
    url: null,
    icon: "🐧",
    label: "для Linux (скоро)",
    ext: ".AppImage",
    size: "—",
    pending: true,
  },
};

export type OSId = keyof typeof DOWNLOADS;

export const RELEASES_PAGE = RELEASES;
export const REPO_PAGE = `https://github.com/${REPO}`;
export const COMING_SOON_FLAG = COMING_SOON;
