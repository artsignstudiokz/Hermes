/**
 * Tiny toast store. Marble-styled, promise-aware, premium.
 *
 * Usage:
 *   import { toast } from "@/lib/toast";
 *   toast.success("Сохранено");
 *   toast.error("Не удалось");
 *   toast.promise(api.post(...), {
 *     loading: "Сохраняю…",
 *     success: "Сохранено",
 *     error:   (e) => `Ошибка: ${e}`,
 *   });
 */

import { useSyncExternalStore } from "react";

export type ToastVariant = "default" | "success" | "error" | "warning" | "loading";

export interface ToastEntry {
  id: number;
  variant: ToastVariant;
  title: string;
  description?: string;
  durationMs: number;
  createdAt: number;
}

let _id = 1;
let _toasts: ToastEntry[] = [];
const listeners = new Set<() => void>();

function emit() {
  for (const fn of listeners) fn();
}

function push(entry: Omit<ToastEntry, "id" | "createdAt">): number {
  const t: ToastEntry = { ...entry, id: _id++, createdAt: Date.now() };
  _toasts = [..._toasts.slice(-4), t];     // cap to 5 stacked
  emit();
  if (entry.durationMs > 0) {
    setTimeout(() => dismiss(t.id), entry.durationMs);
  }
  return t.id;
}

function update(id: number, patch: Partial<Omit<ToastEntry, "id" | "createdAt">>) {
  _toasts = _toasts.map((t) => (t.id === id ? { ...t, ...patch } : t));
  emit();
  if (patch.durationMs && patch.durationMs > 0) {
    setTimeout(() => dismiss(id), patch.durationMs);
  }
}

export function dismiss(id: number) {
  _toasts = _toasts.filter((t) => t.id !== id);
  emit();
}

export const toast = {
  default(title: string, description?: string) {
    return push({ variant: "default", title, description, durationMs: 4000 });
  },
  success(title: string, description?: string) {
    return push({ variant: "success", title, description, durationMs: 3500 });
  },
  error(title: string, description?: string) {
    return push({ variant: "error", title, description, durationMs: 6000 });
  },
  warning(title: string, description?: string) {
    return push({ variant: "warning", title, description, durationMs: 5000 });
  },
  loading(title: string, description?: string) {
    return push({ variant: "loading", title, description, durationMs: 0 });
  },
  promise<T>(
    promise: Promise<T>,
    msgs: {
      loading: string;
      success: string | ((value: T) => string);
      error: string | ((err: unknown) => string);
    },
  ): Promise<T> {
    const id = push({ variant: "loading", title: msgs.loading, durationMs: 0 });
    return promise
      .then((value) => {
        const title = typeof msgs.success === "function" ? msgs.success(value) : msgs.success;
        update(id, { variant: "success", title, durationMs: 3500, description: undefined });
        return value;
      })
      .catch((err) => {
        const title = typeof msgs.error === "function" ? msgs.error(err) : msgs.error;
        update(id, { variant: "error", title, durationMs: 6000, description: undefined });
        throw err;
      });
  },
};

export function useToasts(): ToastEntry[] {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => _toasts,
    () => _toasts,
  );
}
