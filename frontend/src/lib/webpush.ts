/**
 * Web Push helpers — convert VAPID key, request permission, subscribe via SW.
 */

function urlBase64ToUint8Array(b64url: string): Uint8Array {
  const padding = "=".repeat((4 - (b64url.length % 4)) % 4);
  const base64 = (b64url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export interface SerializedSub {
  endpoint: string;
  p256dh: string;
  auth: string;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

export async function ensurePermission(): Promise<NotificationPermission> {
  if (!("Notification" in window)) return "denied";
  if (Notification.permission === "granted") return "granted";
  if (Notification.permission === "denied") return "denied";
  return await Notification.requestPermission();
}

export async function subscribeForPush(vapidPublicKey: string): Promise<SerializedSub> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    throw new Error("Этот браузер не поддерживает push-уведомления");
  }
  const reg = await navigator.serviceWorker.ready;
  const existing = await reg.pushManager.getSubscription();
  if (existing) return serialize(existing);

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });
  return serialize(sub);
}

function serialize(sub: PushSubscription): SerializedSub {
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Подписка некорректна");
  }
  return {
    endpoint: json.endpoint,
    p256dh: json.keys.p256dh,
    auth: json.keys.auth,
  };
}

export function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window
  );
}

export async function unsubscribeFromPush(): Promise<boolean> {
  if (!("serviceWorker" in navigator)) return false;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return false;
  return await sub.unsubscribe();
}

export type { PushSubscription };

declare global {
  interface PushSubscriptionJSON {
    endpoint?: string;
    keys?: {
      p256dh?: string;
      auth?: string;
    };
  }
}

export function arrayBufferToB64(buf: ArrayBuffer): string {
  return arrayBufferToBase64(buf);
}
