import { motion } from "framer-motion";
import { Bell, BellOff, Loader2, Send, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  useDeleteSub,
  useSubscribeTelegram,
  useSubscribeWebPush,
  useSubscriptions,
  useTestNotifications,
  useToggleSub,
  useVapidKey,
} from "@/api/useNotifications";
import {
  ensurePermission,
  isPushSupported,
  subscribeForPush,
  unsubscribeFromPush,
} from "@/lib/webpush";

export function Notifications() {
  const subs = useSubscriptions();
  const vapid = useVapidKey();
  const subscribe = useSubscribeWebPush();
  const subscribeTg = useSubscribeTelegram();
  const toggle = useToggleSub();
  const remove = useDeleteSub();
  const test = useTestNotifications();

  const [error, setError] = useState<string | null>(null);
  const [tgToken, setTgToken] = useState("");
  const [tgChatId, setTgChatId] = useState("");
  const [tgError, setTgError] = useState<string | null>(null);

  const enableWebPush = async () => {
    setError(null);
    if (!isPushSupported()) {
      setError("Браузер не поддерживает push (нужен HTTPS либо localhost)");
      return;
    }
    const perm = await ensurePermission();
    if (perm !== "granted") {
      setError("Разрешение на уведомления не выдано");
      return;
    }
    try {
      const sub = await subscribeForPush(vapid.data?.key ?? "");
      await subscribe.mutateAsync(sub);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось подписаться");
    }
  };

  const disableWebPush = async () => {
    await unsubscribeFromPush();
  };

  const submitTg = async (e: React.FormEvent) => {
    e.preventDefault();
    setTgError(null);
    try {
      await subscribeTg.mutateAsync({ bot_token: tgToken, chat_id: tgChatId });
      setTgToken("");
      setTgChatId("");
    } catch (err) {
      setTgError(err instanceof Error ? err.message : "Не удалось подключить");
    }
  };

  const webpushSubs = (subs.data ?? []).filter((s) => s.type === "webpush");
  const telegramSubs = (subs.data ?? []).filter((s) => s.type === "telegram");

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header>
        <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Уведомления</p>
        <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
          Где получать <span className="gold-text">сигналы Гермеса</span>
        </h1>
        <p className="mt-2 max-w-2xl font-serif italic text-muted-foreground">
          Каждое открытие/закрытие сделки будет приходить на выбранные каналы.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => test.mutate()}
          disabled={test.isPending}
          className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
        >
          {test.isPending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          Отправить тест
        </button>
        {test.data && (
          <span className="text-xs text-muted-foreground">
            Доставлено: web-push <strong>{test.data.webpush}</strong>, telegram <strong>{test.data.telegram}</strong>
          </span>
        )}
      </div>

      {/* Web Push */}
      <section className="marble-card p-6">
        <div className="flex items-center justify-between">
          <h2 className="display text-xl font-semibold">Web Push (браузер)</h2>
          {webpushSubs.length > 0 ? (
            <button
              onClick={disableWebPush}
              className="text-xs text-muted-foreground hover:text-hermes-wine inline-flex items-center gap-1"
            >
              <BellOff size={12} /> Отписаться
            </button>
          ) : (
            <button
              onClick={enableWebPush}
              disabled={subscribe.isPending}
              className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-2 text-sm font-medium hover:bg-hermes-parchment disabled:opacity-50"
            >
              {subscribe.isPending ? <Loader2 size={14} className="animate-spin" /> : <Bell size={14} />}
              Включить
            </button>
          )}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Уведомления приходят прямо в браузер/PWA. После установки PWA на телефон работают как
          нативные.
        </p>
        {error && (
          <div className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}
        <SubList
          subs={webpushSubs}
          onToggle={(id) => toggle.mutate(id)}
          onDelete={(id) => remove.mutate(id)}
        />
      </section>

      {/* Telegram */}
      <section className="marble-card p-6">
        <h2 className="display text-xl font-semibold">Telegram</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Создайте бота через @BotFather и узнайте свой chat_id у @userinfobot.
        </p>
        <form onSubmit={submitTg} className="mt-4 grid gap-3 md:grid-cols-[2fr_1fr_auto]">
          <input
            value={tgToken}
            onChange={(e) => setTgToken(e.target.value)}
            placeholder="Bot token (123456:ABC-DEF...)"
            className="form-input font-mono"
          />
          <input
            value={tgChatId}
            onChange={(e) => setTgChatId(e.target.value)}
            placeholder="Chat ID"
            className="form-input font-mono"
          />
          <button
            type="submit"
            disabled={subscribeTg.isPending || !tgToken || !tgChatId}
            className="gold-button rounded-xl px-5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
          >
            {subscribeTg.isPending ? <Loader2 size={14} className="animate-spin" /> : "Подключить"}
          </button>
        </form>
        {tgError && (
          <div className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {tgError}
          </div>
        )}
        <SubList
          subs={telegramSubs}
          onToggle={(id) => toggle.mutate(id)}
          onDelete={(id) => remove.mutate(id)}
        />
      </section>
    </motion.div>
  );
}

function SubList({
  subs,
  onToggle,
  onDelete,
}: {
  subs: { id: number; endpoint_short: string; enabled: boolean }[];
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  if (subs.length === 0) {
    return (
      <p className="mt-4 font-serif italic text-sm text-muted-foreground">
        Нет активных подписок.
      </p>
    );
  }
  return (
    <ul className="mt-4 divide-y divide-hermes-gold/15">
      {subs.map((s) => (
        <li key={s.id} className="flex items-center justify-between py-2.5">
          <div className="min-w-0 flex-1">
            <code className="block truncate font-mono text-xs">{s.endpoint_short}</code>
          </div>
          <div className="ml-3 flex items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={s.enabled}
                onChange={() => onToggle(s.id)}
                className="h-4 w-4 accent-hermes-gold"
              />
              {s.enabled ? "включено" : "выключено"}
            </label>
            <button
              onClick={() => onDelete(s.id)}
              className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground hover:bg-hermes-wine/15 hover:text-hermes-wine"
              aria-label="Удалить"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
