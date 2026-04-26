/**
 * Bridge to the PyWebView desktop wrapper.
 * Falls back to no-op functions when the app runs in a regular browser
 * (e.g. during `npm run dev` or when accessed remotely via the tunnel).
 */

interface DesktopAPI {
  minimize(): Promise<void>;
  maximize(): Promise<void>;
  close(): Promise<void>;
  open_external(url: string): Promise<void>;
  show_native_notification(title: string, body: string): Promise<void>;
  get_platform(): Promise<{ os: string }>;
}

declare global {
  interface Window {
    pywebview?: { api: DesktopAPI };
  }
}

let cachedReady: Promise<DesktopAPI | null> | null = null;

export function isDesktop(): boolean {
  return typeof window !== "undefined" && window.pywebview != null;
}

/**
 * Resolve the desktop API once it's injected by PyWebView. Times out after
 * ~1500ms in browser mode and resolves to null so callers can no-op.
 */
export function desktop(): Promise<DesktopAPI | null> {
  if (cachedReady) return cachedReady;
  cachedReady = new Promise((resolve) => {
    if (typeof window === "undefined") {
      resolve(null);
      return;
    }
    if (window.pywebview?.api) {
      resolve(window.pywebview.api);
      return;
    }
    const start = Date.now();
    const handle = setInterval(() => {
      if (window.pywebview?.api) {
        clearInterval(handle);
        resolve(window.pywebview.api);
      } else if (Date.now() - start > 1500) {
        clearInterval(handle);
        resolve(null);
      }
    }, 60);
  });
  return cachedReady;
}

export const win = {
  minimize: () => desktop().then((api) => api?.minimize()),
  maximize: () => desktop().then((api) => api?.maximize()),
  close: () => desktop().then((api) => api?.close()),
  openExternal: (url: string) => desktop().then((api) => api?.open_external(url)),
  notify: (title: string, body: string) =>
    desktop().then((api) => api?.show_native_notification(title, body)),
};
