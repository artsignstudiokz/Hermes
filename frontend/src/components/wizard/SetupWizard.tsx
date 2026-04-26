import { motion } from "framer-motion";
import { Check } from "lucide-react";

import { Step1Broker } from "./Step1Broker";
import { Step2Strategy } from "./Step2Strategy";
import { Step3Review } from "./Step3Review";

interface Props {
  step: 1 | 2 | 3;
  onPrev: () => void;
  onNext: () => void;
  onDone: () => void;
}

const TITLES = ["Брокер", "Стратегия", "Запуск"] as const;

export function SetupWizard({ step, onPrev, onNext, onDone }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="marble-card w-full max-w-3xl p-8 md:p-10"
    >
      <Stepper current={step} />

      <div className="mt-8">
        {step === 1 && <Step1Broker onPrev={onPrev} onNext={onNext} />}
        {step === 2 && <Step2Strategy onPrev={onPrev} onNext={onNext} />}
        {step === 3 && <Step3Review onPrev={onPrev} onDone={onDone} />}
      </div>
    </motion.div>
  );
}

function Stepper({ current }: { current: 1 | 2 | 3 }) {
  return (
    <div className="flex items-center justify-between">
      {[1, 2, 3].map((id, i) => {
        const active = id === current;
        const done = id < current;
        return (
          <div key={id} className="flex flex-1 items-center">
            <div className="flex flex-col items-center">
              <div
                className={`grid h-9 w-9 place-items-center rounded-full border text-xs font-semibold transition ${
                  done
                    ? "border-hermes-gold bg-hermes-gold text-hermes-ink"
                    : active
                    ? "border-hermes-gold bg-hermes-gold/15 text-hermes-gold-deep"
                    : "border-hermes-gold/30 bg-card text-muted-foreground"
                }`}
              >
                {done ? <Check size={14} /> : id}
              </div>
              <span
                className={`mt-1.5 text-[10px] uppercase tracking-wider ${
                  active ? "text-hermes-gold-deep" : "text-muted-foreground"
                }`}
              >
                {TITLES[i]}
              </span>
            </div>
            {id < 3 && (
              <div
                className={`mx-2 h-px flex-1 ${
                  id < current ? "bg-hermes-gold" : "bg-hermes-gold/25"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
