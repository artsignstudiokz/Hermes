import { motion } from "framer-motion";
import { CheckCircle2, Trash2 } from "lucide-react";
import { useState } from "react";

import { useActivateBroker, useBrokers, useDeleteBroker } from "@/api/useBrokers";
import { BrokerForm } from "@/components/forms/BrokerForm";

export function Brokers() {
  const brokers = useBrokers();
  const activate = useActivateBroker();
  const remove = useDeleteBroker();
  const [showForm, setShowForm] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header>
        <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Брокеры</p>
        <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
          Подключения к <span className="gold-text">биржам</span>
        </h1>
        <p className="mt-2 max-w-2xl font-serif italic text-muted-foreground">
          Все ключи и пароли шифруются Argon2id + Fernet под мастер-паролем и хранятся только на
          этом компьютере.
        </p>
      </header>

      <section className="space-y-3">
        {brokers.isLoading && (
          <div className="text-sm text-muted-foreground">Загружаю список…</div>
        )}
        {brokers.data?.length === 0 && !showForm && (
          <div className="marble-card grid place-items-center px-6 py-16 text-center">
            <p className="font-serif italic text-lg text-muted-foreground">
              «Чтобы Hermes начал торговать — представьтесь брокеру.»
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="gold-button mt-5 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider"
            >
              Добавить первого брокера
            </button>
          </div>
        )}
        {(brokers.data ?? []).map((b) => (
          <div
            key={b.id}
            className="marble-card flex flex-wrap items-center justify-between gap-4 p-5"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="display text-lg font-semibold">{b.name}</span>
                <span className="rounded-full border border-hermes-gold/40 bg-hermes-alabaster px-2 py-0.5 text-[10px] uppercase tracking-wider text-hermes-gold-deep">
                  {b.type}
                </span>
                {b.is_testnet && (
                  <span className="rounded-full bg-hermes-bronze/15 px-2 py-0.5 text-[10px] uppercase tracking-wider text-hermes-bronze">
                    testnet
                  </span>
                )}
                {b.is_active && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-hermes-laurel/15 px-2 py-0.5 text-[10px] uppercase tracking-wider text-hermes-laurel">
                    <CheckCircle2 size={10} /> активен
                  </span>
                )}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {b.server ? `${b.server}` : "—"}
                {b.login ? ` · ${b.login}` : ""}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!b.is_active && (
                <button
                  onClick={() => activate.mutate(b.id)}
                  disabled={activate.isPending}
                  className="rounded-lg border border-hermes-gold/40 bg-hermes-alabaster px-3 py-1.5 text-xs font-medium hover:bg-hermes-parchment"
                >
                  Сделать активным
                </button>
              )}
              <button
                onClick={() => remove.mutate(b.id)}
                disabled={remove.isPending}
                className="grid h-8 w-8 place-items-center rounded-lg text-muted-foreground hover:bg-hermes-wine/15 hover:text-hermes-wine"
                aria-label="Удалить"
                title="Удалить"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
        {(brokers.data?.length ?? 0) > 0 && !showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-xl border border-dashed border-hermes-gold/40 bg-transparent px-5 py-3 text-sm text-muted-foreground hover:bg-hermes-parchment/40"
          >
            + Добавить ещё одного брокера
          </button>
        )}
      </section>

      {showForm && (
        <BrokerForm onCreated={() => setShowForm(false)} />
      )}
    </motion.div>
  );
}
