import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface NotificationSub {
  id: number;
  type: "webpush" | "telegram";
  endpoint_short: string;
  enabled: boolean;
}

export function useVapidKey() {
  return useQuery({
    queryKey: ["vapid-public"],
    queryFn: () => api.get<{ key: string }>("/api/notifications/vapid-public"),
    staleTime: Infinity,
  });
}

export function useSubscriptions() {
  return useQuery({
    queryKey: ["notification-subs"],
    queryFn: () => api.get<NotificationSub[]>("/api/notifications/subs"),
  });
}

export function useSubscribeWebPush() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { endpoint: string; p256dh: string; auth: string }) =>
      api.post<NotificationSub>("/api/notifications/webpush/subscribe", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-subs"] }),
  });
}

export function useSubscribeTelegram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { bot_token: string; chat_id: string }) =>
      api.post<NotificationSub>("/api/notifications/telegram/subscribe", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-subs"] }),
  });
}

export function useToggleSub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.patch<NotificationSub>(`/api/notifications/${id}/toggle`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-subs"] }),
  });
}

export function useDeleteSub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/notifications/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-subs"] }),
  });
}

export function useTestNotifications() {
  return useMutation({
    mutationFn: () => api.post<{ webpush: number; telegram: number }>("/api/notifications/test"),
  });
}
