import { CheckCircle2, ChevronLeft, ChevronRight, Loader2, XCircle } from "lucide-react";
import { useState } from "react";

import { useCreateBroker, useTestBroker, type BrokerCreateInput } from "@/api/useBrokers";
import { useMt5Servers } from "@/api/useOnboarding";
import { ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

interface Props {
  onPrev: () => void;
  onNext: () => void;
}

type BrokerType = BrokerCreateInput["type"];

export function Step1Broker({ onPrev, onNext }: Props) {
  const [type, setType] = useState<BrokerType>("mt5");
  const [name, setName] = useState("");
  const [server, setServer] = useState("");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [apiPassphrase, setApiPassphrase] = useState("");
  const [testnet, setTestnet] = useState(false);

  const servers = useMt5Servers();
  const test = useTestBroker();
  const create = useCreateBroker();
  const [created, setCreated] = useState(false);

  const buildPayload = (): Omit<BrokerCreateInput, "name"> => ({
    type,
    server: type === "mt5" ? server : undefined,
    login: type === "mt5" && login ? Number(login) : undefined,
    password: type === "mt5" ? password : undefined,
    api_key: type !== "mt5" ? apiKey : undefined,
    api_secret: type !== "mt5" ? apiSecret : undefined,
    api_passphrase: type === "okx" ? apiPassphrase : undefined,
    testnet,
  });

  const onTest = async () => {
    await test.mutateAsync(buildPayload());
  };

  const onSave = async () => {
    const payload = buildPayload();
    try {
      await create.mutateAsync({
        ...payload,
        name: name || `${type.toUpperCase()} ${login || apiKey?.slice(0, 6)}`.trim(),
      });
      setCreated(true);
      toast.success("Брокер сохранён");
      onNext();
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : err instanceof Error ? err.message : String(err);
      toast.error("Не удалось сохранить", detail);
    }
  };

  const isMt5 = type === "mt5";

  return (
    <div className="space-y-5">
      <div>
        <h2 className="display text-3xl font-semibold gold-text">Подключите брокера</h2>
        <p className="mt-2 font-serif italic text-muted-foreground">
          Hermes свяжется с вашим счётом. Все ключи и пароли шифруются мастер-паролем.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        {(["mt5", "binance", "bybit", "okx"] as BrokerType[]).map((t) => (
          <button
            key={t}
            onClick={() => setType(t)}
            className={`rounded-xl border px-3 py-2 text-sm font-medium uppercase tracking-wider transition ${
              type === t
                ? "border-hermes-gold-deep bg-hermes-gold/15 text-hermes-gold-deep"
                : "border-hermes-gold/30 text-muted-foreground hover:bg-hermes-parchment/50"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Название счёта (для удобства)">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Например: Демо XM"
            className="form-input"
          />
        </Field>

        {isMt5 ? (
          <>
            <Field label="Сервер брокера">
              <input
                value={server}
                onChange={(e) => setServer(e.target.value)}
                list="onboarding-mt5-servers"
                placeholder="Начните вводить — найду сами"
                className="form-input"
              />
              <datalist id="onboarding-mt5-servers">
                {(servers.data ?? []).map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.broker ? `${s.broker}` : ""}
                  </option>
                ))}
              </datalist>
              {servers.data && servers.data.length > 0 && (
                <p className="mt-1 text-[10px] text-muted-foreground">
                  Найдено серверов: {servers.data.length} (из локальных терминалов MT5)
                </p>
              )}
            </Field>
            <Field label="Логин (номер счёта)">
              <input
                inputMode="numeric"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                placeholder="12345678"
                className="form-input font-mono"
              />
            </Field>
            <Field label="Инвестор-пароль">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="form-input font-mono"
              />
            </Field>
          </>
        ) : (
          <>
            <Field label="API Key">
              <input
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="form-input font-mono"
              />
            </Field>
            <Field label="API Secret">
              <input
                type="password"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                className="form-input font-mono"
              />
            </Field>
            {type === "okx" && (
              <Field label="API Passphrase">
                <input
                  type="password"
                  value={apiPassphrase}
                  onChange={(e) => setApiPassphrase(e.target.value)}
                  className="form-input font-mono"
                />
              </Field>
            )}
            <Field label="Тестовая сеть">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={testnet}
                  onChange={(e) => setTestnet(e.target.checked)}
                  className="h-4 w-4 accent-hermes-gold"
                />
                Использовать testnet (без реальных средств)
              </label>
            </Field>
          </>
        )}
      </div>

      {test.data && (
        <div
          className={`rounded-xl border p-4 text-sm ${
            test.data.ok
              ? "border-hermes-laurel/40 bg-hermes-laurel/10"
              : "border-hermes-wine/40 bg-hermes-wine/10"
          }`}
        >
          {test.data.ok ? (
            <div className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 text-hermes-laurel" size={16} />
              <div>
                <div className="font-semibold">Подключение успешно</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Баланс: {test.data.balance} {test.data.currency} · Плечо 1:{test.data.leverage}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2">
              <XCircle className="mt-0.5 text-hermes-wine" size={16} />
              <div>
                <div className="font-semibold">Не удалось подключиться</div>
                <div className="mt-1 text-xs text-muted-foreground">{test.data.error}</div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <button
          onClick={onPrev}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft size={14} /> Назад
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={onTest}
            disabled={test.isPending}
            className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-2.5 text-sm font-medium hover:bg-hermes-parchment disabled:opacity-50"
          >
            {test.isPending && <Loader2 size={14} className="animate-spin" />}
            Проверить
          </button>
          <button
            onClick={onSave}
            disabled={!test.data?.ok || create.isPending || created}
            className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
          >
            {create.isPending && <Loader2 size={14} className="animate-spin" />}
            {created ? "Сохранено" : "Сохранить и далее"} <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}
