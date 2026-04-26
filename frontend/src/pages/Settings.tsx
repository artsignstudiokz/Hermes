import { motion } from "framer-motion";
import { CheckCircle2, ExternalLink, Loader2, Moon, RefreshCw, Sun, Sunrise } from "lucide-react";
import { useEffect } from "react";

import { useCheckUpdate, useVersion } from "@/api/useSystem";
import { useTheme } from "@/theme/ThemeProvider";
import { win } from "@/lib/webview";
import { brand } from "@/theme/tokens";

export function Settings() {
  const version = useVersion();
  const update = useCheckUpdate();
  const { theme, setTheme } = useTheme();

  // Auto-check on first mount (one-shot, fire-and-forget).
  useEffect(() => {
    update.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const u = update.data;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header>
        <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Настройки</p>
        <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
          Параметры <span className="gold-text">приложения</span>
        </h1>
      </header>

      {/* Theme */}
      <section className="marble-card p-6">
        <h2 className="display text-xl font-semibold">Тема оформления</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          По умолчанию — мраморная (светлая). Тёмная подойдёт для ночной торговли.
        </p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <ThemeOption
            icon={Sunrise}
            label="Мраморная"
            value="light"
            current={theme}
            onSelect={setTheme}
            hint="Светлая, по умолчанию"
          />
          <ThemeOption
            icon={Moon}
            label="Полночная"
            value="dark"
            current={theme}
            onSelect={setTheme}
            hint="Тёмная — для ночи"
          />
          <ThemeOption
            icon={Sun}
            label="Системная"
            value="system"
            current={theme}
            onSelect={setTheme}
            hint="Следует за ОС"
          />
        </div>
      </section>

      {/* Updates */}
      <section className="marble-card p-6">
        <div className="flex items-center justify-between">
          <h2 className="display text-xl font-semibold">Обновления</h2>
          <button
            onClick={() => update.mutate()}
            disabled={update.isPending}
            className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-2 text-sm font-medium hover:bg-hermes-parchment disabled:opacity-50"
          >
            {update.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Проверить
          </button>
        </div>
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <Row label="Текущая версия" value={version.data?.version ?? u?.current_version ?? "—"} />
          <Row label="Доступная версия" value={u?.latest_version ?? "—"} />
        </div>
        {u && u.has_update && (
          <div className="mt-5 rounded-xl border border-hermes-gold-deep/40 bg-hermes-gold/10 p-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 text-hermes-gold-deep" size={18} />
              <div className="flex-1">
                <div className="font-semibold">
                  Доступна версия {u.latest_version}
                </div>
                {u.released_at && (
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    Выпущена {new Date(u.released_at).toLocaleDateString("ru-RU")}
                  </div>
                )}
                {u.notes && (
                  <pre className="mt-3 max-h-40 overflow-auto rounded-md bg-hermes-marble p-3 text-xs leading-relaxed whitespace-pre-wrap font-sans">
                    {u.notes}
                  </pre>
                )}
                {u.asset && (
                  <button
                    onClick={() => u.asset && win.openExternal(u.asset.url)}
                    className="gold-button mt-4 inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold uppercase tracking-wider"
                  >
                    <ExternalLink size={14} /> Скачать ({(u.asset.size / 1024 / 1024).toFixed(1)} МБ)
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
        {u && !u.has_update && !update.isPending && (
          <div className="mt-5 rounded-xl border border-hermes-laurel/40 bg-hermes-laurel/10 p-3 text-sm text-hermes-laurel">
            <CheckCircle2 size={14} className="mr-2 inline" />
            У вас актуальная версия Hermes.
          </div>
        )}
        {update.isError && (
          <div className="mt-5 rounded-xl border border-hermes-bronze/40 bg-hermes-bronze/10 p-3 text-sm text-hermes-bronze">
            Не удалось связаться с сервером обновлений. Возможно, нет интернета.
          </div>
        )}
      </section>

      {/* About snippet */}
      <section className="marble-card p-6">
        <h2 className="display text-xl font-semibold">О приложении</h2>
        <div className="mt-3 grid gap-2 text-sm">
          <Row label="Продукт" value={version.data?.product ?? brand.productFull} />
          <Row label="Разработчик" value={version.data?.brand ?? brand.developer} />
          <Row label="Сайт" value="baicore.kz" />
          <Row label="Поддержка" value="info@baicore.kz" />
        </div>
        <button
          onClick={() => win.openExternal(brand.developerUrl)}
          className="mt-4 inline-flex items-center gap-2 text-sm text-hermes-aegean hover:underline"
        >
          <ExternalLink size={14} /> Открыть сайт BAI Core
        </button>
      </section>
    </motion.div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-hermes-gold/15 py-1.5 last:border-b-0">
      <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function ThemeOption({
  icon: Icon,
  label,
  value,
  current,
  onSelect,
  hint,
}: {
  icon: typeof Moon;
  label: string;
  value: "light" | "dark" | "system";
  current: string;
  onSelect: (v: "light" | "dark" | "system") => void;
  hint: string;
}) {
  const active = current === value;
  return (
    <button
      onClick={() => onSelect(value)}
      className={`group flex flex-col items-start gap-1 rounded-xl border p-4 text-left transition ${
        active
          ? "border-hermes-gold-deep bg-hermes-gold/15 shadow-gold"
          : "border-hermes-gold/30 bg-hermes-alabaster hover:bg-hermes-parchment/60"
      }`}
    >
      <Icon
        size={20}
        className={active ? "text-hermes-gold-deep" : "text-muted-foreground group-hover:text-hermes-gold-deep"}
      />
      <span className="display text-base font-semibold">{label}</span>
      <span className="text-xs text-muted-foreground">{hint}</span>
    </button>
  );
}
