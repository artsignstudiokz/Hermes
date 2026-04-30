import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Check, ChevronRight, Lock, Shield, Sparkles } from "lucide-react";

import { BrandMark } from "@/components/ui/BrandMark";
import { SetupWizard } from "@/components/wizard/SetupWizard";
import { api, ApiError, setAuthToken } from "@/lib/api";
import { useOnboardingStatus } from "@/api/useOnboarding";

interface TokenResponse {
  token: string;
  expires_at: string;
}

type Phase = "welcome" | "password" | "wizard" | "done";

export function Onboarding() {
  const status = useOnboardingStatus();
  const [phase, setPhase] = useState<Phase>("welcome");
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Skip phases that are already done — handles refresh mid-onboarding.
  useEffect(() => {
    if (!status.data) return;
    if (status.data.first_run) {
      setPhase("welcome");
    } else if (!status.data.has_broker) {
      setPhase("wizard");
      setStep(1);
    } else if (!status.data.has_strategy) {
      setPhase("wizard");
      setStep(2);
    } else if (!status.data.is_running) {
      setPhase("wizard");
      setStep(3);
    } else {
      setPhase("done");
    }
  }, [status.data]);

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-10">
      <div
        aria-hidden
        className="absolute inset-x-0 top-12 h-5 opacity-30"
        style={{ backgroundImage: "url('/meander.svg')", backgroundRepeat: "repeat-x" }}
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-12 h-5 opacity-30 rotate-180"
        style={{ backgroundImage: "url('/meander.svg')", backgroundRepeat: "repeat-x" }}
      />

      {phase === "welcome" && <Welcome onNext={() => setPhase("password")} />}
      {phase === "password" && (
        <PasswordSetup onNext={() => { setPhase("wizard"); setStep(1); }} />
      )}
      {phase === "wizard" && (
        <SetupWizard
          step={step}
          onPrev={() => {
            if (step > 1) setStep(((step - 1) as 1 | 2));
            else setPhase("password");
          }}
          onNext={() => setStep((s) => (s < 3 ? ((s + 1) as 2 | 3) : s))}
          onDone={() => location.assign("/")}
        />
      )}
      {phase === "done" && (
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="marble-card w-full max-w-md p-10 text-center"
        >
          <div className="grid place-items-center">
            <div className="grid h-20 w-20 place-items-center rounded-full bg-hermes-gold/15 text-hermes-gold-deep">
              <Check size={40} />
            </div>
          </div>
          <h1 className="display mt-4 text-3xl font-semibold gold-text">Всё настроено</h1>
          <p className="mt-2 font-serif italic text-muted-foreground">
            «Жду вашего знака — нажмите «Запустить» на панели, когда будете готовы.»
          </p>
          <button
            onClick={() => location.assign("/")}
            className="gold-button mt-6 rounded-xl px-6 py-3 text-sm font-semibold uppercase tracking-wider"
          >
            На Олимп
          </button>
        </motion.div>
      )}
    </div>
  );
}

function Welcome({ onNext }: { onNext: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="marble-card w-full max-w-2xl p-10 text-center"
    >
      <div className="flex justify-center">
        <BrandMark size="lg" showText={false} />
      </div>
      <h1 className="display mt-6 text-5xl font-semibold gold-text">Добро пожаловать в Hermes</h1>
      <p className="mt-3 font-serif text-xl italic text-muted-foreground">
        Покровитель торговцев теперь у вас на столе.
      </p>

      <div className="mt-8 grid gap-4 text-left sm:grid-cols-3">
        <Feature
          icon={Shield}
          title="Безопасно"
          text="Ключи бирж шифруются Argon2id + Fernet под мастер-паролем."
        />
        <Feature
          icon={Sparkles}
          title="Адаптивно"
          text="Hermes еженедельно пересчитывает параметры под рынок."
        />
        <Feature
          icon={Lock}
          title="Локально"
          text="Все данные на вашем компьютере. Никаких облаков."
        />
      </div>

      <button
        onClick={onNext}
        className="gold-button mt-8 inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold uppercase tracking-wider"
      >
        Начать <ChevronRight size={14} />
      </button>
    </motion.div>
  );
}

function PasswordSetup({ onNext }: { onNext: () => void }) {
  const [pwd, setPwd] = useState("");
  const [pwd2, setPwd2] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (pwd.length < 6) return setError("Минимум 6 символов");
    if (pwd !== pwd2) return setError("Пароли не совпадают");
    setBusy(true);
    try {
      const r = await api.post<TokenResponse, { master_password: string }>(
        "/api/auth/setup-master-password",
        { master_password: pwd },
      );
      setAuthToken(r.token);
      onNext();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось");
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="marble-card w-full max-w-md p-10"
    >
      <BrandMark size="md" />
      <h2 className="display mt-6 text-3xl font-semibold gold-text">Создайте мастер-пароль</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Этот пароль шифрует все ключи API ваших бирж. Запишите его в надёжное место —
        восстановить нельзя.
      </p>

      <form onSubmit={submit} className="mt-5 space-y-4">
        <Field label="Мастер-пароль">
          <input
            type="password"
            value={pwd}
            onChange={(e) => setPwd(e.target.value)}
            autoFocus
            className="form-input font-mono"
            placeholder="Минимум 6 символов"
          />
        </Field>
        <Field label="Повторите пароль">
          <input
            type="password"
            value={pwd2}
            onChange={(e) => setPwd2(e.target.value)}
            className="form-input font-mono"
            placeholder="Ещё раз"
          />
        </Field>
        {error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={busy}
          className="gold-button w-full rounded-lg py-3 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
        >
          {busy ? "Запечатываю свиток…" : "Создать пароль"}
        </button>
      </form>
    </motion.div>
  );
}

function Feature({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof Shield;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-xl border border-hermes-gold/30 bg-hermes-alabaster/60 p-4">
      <Icon size={20} className="mb-2 text-hermes-gold-deep" />
      <div className="font-serif text-base font-semibold">{title}</div>
      <p className="mt-1 text-sm text-muted-foreground">{text}</p>
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
