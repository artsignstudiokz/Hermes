import { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

import {
  useCreateBroker,
  useTestBroker,
  type BrokerCreateInput,
} from "@/api/useBrokers";

const POPULAR_MT5_SERVERS = [
  "Exness-MT5Trial",
  "Exness-MT5Real",
  "RoboForex-MetaTrader5",
  "RoboForex-Demo",
  "XMGlobal-MT5",
  "FBS-Demo",
  "FBS-Real",
  "Alpari-MT5",
  "MetaQuotes-Demo",
];

interface Props {
  onCreated?: () => void;
}

type BrokerType = BrokerCreateInput["type"];

export function BrokerForm({ onCreated }: Props) {
  const [type, setType] = useState<BrokerType>("mt5");
  const [name, setName] = useState("");
  const [server, setServer] = useState("");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [apiPassphrase, setApiPassphrase] = useState("");
  const [testnet, setTestnet] = useState(false);

  const test = useTestBroker();
  const create = useCreateBroker();
  const [step, setStep] = useState<"idle" | "tested" | "created">("idle");

  const buildPayload = (): BrokerCreateInput => ({
    name: name || `${type.toUpperCase()} ${login || apiKey?.slice(0, 6) || ""}`.trim(),
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
    const payload = buildPayload();
    const { name: _ignore, ...rest } = payload;
    await test.mutateAsync(rest);
    setStep("tested");
  };

  const onSave = async () => {
    await create.mutateAsync(buildPayload());
    setStep("created");
    onCreated?.();
  };

  const isMt5 = type === "mt5";
  const okx = type === "okx";

  return (
    <div className="marble-card p-6">
      <h3 className="display text-xl font-semibold">Подключить брокера</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Введите данные счёта и проверьте подключение перед сохранением.
      </p>

      <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-4">
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

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <Field label="Название счёта">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Например: Демо XM"
            className="form-input"
          />
        </Field>

        {isMt5 ? (
          <>
            <Field label="Сервер">
              <input
                value={server}
                onChange={(e) => setServer(e.target.value)}
                list="mt5-servers"
                placeholder="Например, MetaQuotes-Demo"
                className="form-input"
              />
              <datalist id="mt5-servers">
                {POPULAR_MT5_SERVERS.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>
            </Field>
            <Field label="Логин">
              <input
                inputMode="numeric"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                placeholder="12345678"
                className="form-input font-mono"
              />
            </Field>
            <Field label="Пароль">
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
            {okx && (
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
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-5 rounded-xl border p-4 text-sm ${
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
                  {test.data.server} · Баланс: {test.data.balance} {test.data.currency} · Плечо 1:{test.data.leverage}
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
        </motion.div>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          onClick={onTest}
          disabled={test.isPending}
          className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-2.5 text-sm font-medium hover:bg-hermes-parchment disabled:opacity-50"
        >
          {test.isPending && <Loader2 size={14} className="animate-spin" />}
          Проверить подключение
        </button>
        <button
          onClick={onSave}
          disabled={!test.data?.ok || create.isPending || step === "created"}
          className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
        >
          {create.isPending && <Loader2 size={14} className="animate-spin" />}
          {step === "created" ? "Сохранено" : "Сохранить и зашифровать"}
        </button>
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
