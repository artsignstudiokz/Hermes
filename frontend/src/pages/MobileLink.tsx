import { motion } from "framer-motion";
import { Copy, Loader2, Power, RefreshCw, Smartphone, Wifi, WifiOff } from "lucide-react";
import { useState } from "react";

import {
  useRegenPin,
  useStartTunnel,
  useStopTunnel,
  useTunnelStatus,
} from "@/api/useTunnel";

export function MobileLink() {
  const status = useTunnelStatus();
  const start = useStartTunnel();
  const stop = useStopTunnel();
  const regen = useRegenPin();
  const [copied, setCopied] = useState(false);

  const data = status.data;
  const url = data?.url ?? null;
  const pin = data?.pin ?? null;
  const active = data?.active ?? false;

  const copyLink = async () => {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header>
        <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Удалённый доступ</p>
        <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
          Hermes <span className="gold-text">на телефоне</span>
        </h1>
        <p className="mt-2 max-w-2xl font-serif italic text-muted-foreground">
          Один QR — и весь интерфейс открывается на iPhone или Android. Защита через
          одноразовый PIN, который меняется раз в сутки.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <section className="marble-card p-6">
          <div className="flex items-baseline justify-between">
            <h2 className="display text-xl font-semibold">Состояние</h2>
            <div
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
                active
                  ? "bg-hermes-laurel/15 text-hermes-laurel"
                  : "bg-hermes-parchment/60 text-muted-foreground"
              }`}
            >
              {active ? <Wifi size={12} /> : <WifiOff size={12} />}
              {active ? "Активен" : "Выключен"}
            </div>
          </div>

          <div className="mt-5 space-y-3">
            <Detail label="Адрес">
              <div className="flex items-center gap-2">
                <code className="block flex-1 truncate rounded-lg border border-hermes-gold/30 bg-hermes-alabaster px-3 py-2 font-mono text-xs">
                  {url ?? "—"}
                </code>
                <button
                  onClick={copyLink}
                  disabled={!url}
                  className="grid h-9 w-9 place-items-center rounded-lg border border-hermes-gold/40 bg-hermes-alabaster text-muted-foreground hover:bg-hermes-parchment hover:text-foreground disabled:opacity-40"
                  aria-label="Скопировать"
                  title={copied ? "Скопировано" : "Копировать"}
                >
                  <Copy size={14} />
                </button>
              </div>
              {copied && (
                <span className="mt-1 inline-block text-[10px] text-hermes-laurel">Скопировано</span>
              )}
            </Detail>

            <Detail label="PIN-код">
              <div className="flex items-center gap-2">
                <div className="flex-1 rounded-lg border border-hermes-gold/30 bg-hermes-alabaster px-3 py-2 font-mono text-xl tracking-[0.3em]">
                  {pin ?? "—"}
                </div>
                <button
                  onClick={() => regen.mutate()}
                  disabled={!active || regen.isPending}
                  className="grid h-9 w-9 place-items-center rounded-lg border border-hermes-gold/40 bg-hermes-alabaster text-muted-foreground hover:bg-hermes-parchment hover:text-foreground disabled:opacity-40"
                  aria-label="Сгенерировать новый PIN"
                  title="Новый PIN"
                >
                  <RefreshCw size={14} />
                </button>
              </div>
            </Detail>
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            {!active ? (
              <button
                onClick={() => start.mutate()}
                disabled={start.isPending}
                className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
              >
                {start.isPending ? <Loader2 size={14} className="animate-spin" /> : <Power size={14} />}
                Открыть туннель
              </button>
            ) : (
              <button
                onClick={() => stop.mutate()}
                disabled={stop.isPending}
                className="inline-flex items-center gap-2 rounded-xl border border-hermes-wine/40 bg-hermes-wine/10 px-5 py-2.5 text-sm font-medium text-hermes-wine hover:bg-hermes-wine/15 disabled:opacity-50"
              >
                {stop.isPending && <Loader2 size={14} className="animate-spin" />}
                Закрыть туннель
              </button>
            )}
          </div>

          {start.error && (
            <p className="mt-3 text-xs text-hermes-wine">
              Не удалось поднять туннель: {(start.error as Error).message}. Возможно, нужен ngrok-токен —
              задайте через переменную окружения <code className="font-mono">BCT_NGROK_AUTHTOKEN</code>.
            </p>
          )}
        </section>

        <section className="marble-card flex flex-col items-center p-6 text-center">
          <h2 className="display text-xl font-semibold">Сканируйте QR</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Откроется интерфейс Hermes в браузере телефона
          </p>
          <div className="mt-5 grid h-64 w-64 place-items-center rounded-xl border border-hermes-gold/30 bg-hermes-marble p-2 shadow-marble">
            {data?.qr ? (
              <img src={data.qr} alt="QR код для мобильного доступа" className="h-full w-full" />
            ) : (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <Smartphone size={36} />
                <span className="text-xs">Активируйте туннель — QR появится</span>
              </div>
            )}
          </div>
          <p className="mt-4 max-w-xs text-xs text-muted-foreground">
            На телефоне откроется PWA — вы сможете «Установить на главный экран» как полноценное
            приложение.
          </p>
        </section>
      </div>

      <section className="marble-card p-6 text-sm">
        <h2 className="display text-lg font-semibold">Как это работает</h2>
        <ol className="mt-3 space-y-2 text-muted-foreground">
          <li><span className="text-hermes-gold-deep">①</span> Нажмите «Открыть туннель» — Hermes откроет защищённый ngrok-канал.</li>
          <li><span className="text-hermes-gold-deep">②</span> Отсканируйте QR с телефона. Откроется тот же интерфейс.</li>
          <li><span className="text-hermes-gold-deep">③</span> Введите 6-значный PIN. После 5 неудачных попыток туннель блокируется на 10 минут.</li>
          <li><span className="text-hermes-gold-deep">④</span> Когда не нужно — нажмите «Закрыть туннель». Внешний доступ выключен.</li>
        </ol>
      </section>
    </motion.div>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      {children}
    </div>
  );
}
