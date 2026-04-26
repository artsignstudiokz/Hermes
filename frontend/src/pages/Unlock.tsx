import { motion } from "framer-motion";
import { useState } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";

import { BrandMark } from "@/components/ui/BrandMark";
import { api, ApiError, setAuthToken } from "@/lib/api";

interface TokenResponse {
  token: string;
  expires_at: string;
}

export function Unlock({ onUnlocked }: { onUnlocked: () => void }) {
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await api.post<TokenResponse, { master_password: string }>(
        "/api/auth/unlock",
        { master_password: password },
      );
      setAuthToken(r.token);
      onUnlocked();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Неизвестная ошибка");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6">
      {/* Decorative top meander */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-12 h-5 opacity-30"
        style={{ backgroundImage: "url('/meander.svg')", backgroundRepeat: "repeat-x" }}
      />

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        className="marble-card relative w-full max-w-md p-10"
      >
        <div className="flex flex-col items-center gap-6">
          <BrandMark size="lg" showText={false} />
          <div className="text-center">
            <h1 className="display text-4xl font-semibold gold-text">Hermes</h1>
            <p className="mt-2 font-serif italic text-muted-foreground">
              «Введи мастер-пароль и я открою тебе путь.»
            </p>
          </div>

          <form onSubmit={submit} className="mt-2 w-full space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Мастер-пароль
              </span>
              <div className="relative">
                <Lock
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-hermes-gold-deep"
                />
                <input
                  type={showPwd ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoFocus
                  required
                  className="w-full rounded-lg border border-hermes-gold/40 bg-card px-10 py-3 font-mono text-sm outline-none transition focus:border-hermes-gold focus:ring-2 focus:ring-hermes-gold/30"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPwd ? "Скрыть" : "Показать"}
                >
                  {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </label>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </motion.div>
            )}

            <button
              type="submit"
              disabled={busy || !password}
              className="gold-button w-full rounded-lg py-3 text-sm font-semibold uppercase tracking-wider transition disabled:opacity-50"
            >
              {busy ? "Открываю врата…" : "Войти"}
            </button>
          </form>

          <div className="mt-2 flex items-center gap-3 text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span className="h-px w-10 bg-hermes-gold/40" />
            <span>Разработано BAI Core</span>
            <span className="h-px w-10 bg-hermes-gold/40" />
          </div>
        </div>
      </motion.div>
    </div>
  );
}
