/**
 * Hermes — push notification service worker.
 * Registered automatically by vite-plugin-pwa; this file is its addition for
 * receiving Web Push events. The PWA shell SW handles caching and updates.
 */

self.addEventListener("push", (event) => {
  const data = (() => {
    try { return event.data?.json() ?? {}; } catch { return {}; }
  })();
  const title = data.title || "Hermes";
  const body = data.body || "Новое событие";
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: data.icon || "/hermes-emblem.svg",
      badge: data.badge || "/hermes-emblem.svg",
      tag: "hermes-signal",
      renotify: true,
      data: data.data || {},
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const target = clients.find((c) => c.url.includes("/")) || clients[0];
      if (target) return target.focus();
      return self.clients.openWindow("/");
    }),
  );
});
