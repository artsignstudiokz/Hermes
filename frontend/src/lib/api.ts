/**
 * Minimal typed fetch wrapper. Auth token (JWT) is stored in memory only —
 * the desktop window restart effectively logs the user out, which is what
 * we want for a local trading app.
 */

let token: string | null = null;

export function setAuthToken(t: string | null): void {
  token = t;
}

export function getAuthToken(): string | null {
  return token;
}

const BASE = ""; // same-origin (FastAPI serves the SPA)

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const r = await fetch(BASE + path, { ...init, headers, credentials: "include" });
  if (!r.ok) {
    let detail: string;
    try {
      const body = (await r.json()) as { detail?: string };
      detail = body.detail ?? r.statusText;
    } catch {
      detail = r.statusText;
    }
    throw new ApiError(r.status, detail);
  }
  if (r.status === 204) return undefined as unknown as T;
  return (await r.json()) as T;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export const api = {
  get: <T,>(p: string) => apiFetch<T>(p),
  post: <T, B = unknown>(p: string, body?: B) =>
    apiFetch<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T, B = unknown>(p: string, body?: B) =>
    apiFetch<T>(p, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  patch: <T, B = unknown>(p: string, body?: B) =>
    apiFetch<T>(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T,>(p: string) => apiFetch<T>(p, { method: "DELETE" }),
};
