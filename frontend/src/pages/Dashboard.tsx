import { motion } from "framer-motion";
import { Coins, Gauge, Pause, Play, Power, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

import { useAccount, useEquityHistory, useTradingStatus } from "@/api/useAccount";
import { useBrokers } from "@/api/useBrokers";
import { usePositions } from "@/api/usePositions";
import { useTradeStats } from "@/api/useTrades";
import {
  usePauseTrading,
  useResumeTrading,
  useStartTrading,
  useStopTrading,
} from "@/api/useTrading";
import { useStrategyConfig } from "@/api/useStrategy";
import { EquityChart } from "@/components/charts/EquityChart";
import { RegimeBadge } from "@/components/charts/RegimeBadge";
import { PositionsTable } from "@/components/tables/PositionsTable";
import { BalanceCard } from "@/components/widgets/BalanceCard";
import { BotStatusBadge } from "@/components/widgets/BotStatusBadge";
import { KillSwitch } from "@/components/widgets/KillSwitch";
import { RiskGauge } from "@/components/widgets/RiskGauge";
import { SignalToasts } from "@/components/widgets/SignalToast";
import { useRegime } from "@/api/useAdaptive";
import { formatMoney, formatPct } from "@/lib/format";

export function Dashboard() {
  const account = useAccount();
  const positions = usePositions();
  const stats = useTradeStats(30);
  const status = useTradingStatus();
  const brokers = useBrokers();
  const config = useStrategyConfig();
  const regime = useRegime();

  const activeBroker = brokers.data?.find((b) => b.is_active) ?? null;
  const equityHistory = useEquityHistory(activeBroker?.id ?? null, 30);

  const start = useStartTrading();
  const stop = useStopTrading();
  const pause = usePauseTrading();
  const resume = useResumeTrading();

  const running = status.data?.worker?.running ?? false;
  const paused = status.data?.worker?.paused ?? false;

  const stopPct = (config.data?.payload?.stop_drawdown_pct ?? 10) / 100;
  const hardPct = (config.data?.payload?.max_portfolio_drawdown_pct ?? 20) / 100;
  const peakEquity = (equityHistory.data ?? []).reduce(
    (m, p) => Math.max(m, p.equity),
    account.data?.equity ?? 0,
  );
  const drawdown = peakEquity > 0 && account.data
    ? Math.max(0, (peakEquity - account.data.equity) / peakEquity)
    : 0;

  const onPrimary = () => {
    if (!activeBroker) return;
    if (!running) start.mutate(activeBroker.id);
    else if (paused) resume.mutate();
    else pause.mutate();
  };

  const primaryLabel = !running ? "Запустить" : paused ? "Возобновить" : "Пауза";
  const PrimaryIcon = !running ? Power : paused ? Play : Pause;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <SignalToasts />

      <header className="flex flex-col items-start justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <div className="flex items-center gap-3">
            <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Олимп</p>
            <BotStatusBadge />
            {regime.data && <RegimeBadge regime={regime.data.regime} />}
          </div>
          <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
            {activeBroker
              ? <>Счёт <span className="gold-text">{activeBroker.name}</span></>
              : <>Подключите <span className="gold-text">брокера</span></>}
          </h1>
          <p className="mt-1 max-w-2xl font-serif italic text-muted-foreground">
            «Нет дома богаче того, в котором живёт Гермес — посланник прибыли.»
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!activeBroker ? (
            <Link
              to="/brokers"
              className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold uppercase tracking-wider"
            >
              Подключить брокера
            </Link>
          ) : (
            <>
              <button
                onClick={onPrimary}
                disabled={start.isPending || pause.isPending || resume.isPending}
                className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold uppercase tracking-wider"
              >
                <PrimaryIcon size={16} /> {primaryLabel}
              </button>
              {running && (
                <button
                  onClick={() => stop.mutate()}
                  disabled={stop.isPending}
                  className="rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-3 text-sm font-medium hover:bg-hermes-parchment"
                >
                  Остановить
                </button>
              )}
            </>
          )}
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <BalanceCard account={account.data} loading={account.isLoading} />
        <Kpi
          label="Сегодня"
          value={formatMoney(stats.data?.pnl_total ?? 0)}
          hint="P&L за 30 дней"
          icon={TrendingUp}
          tone="success"
        />
        <RiskGauge drawdown={drawdown} stop={stopPct} hardStop={hardPct} />
        <Kpi
          label="Win-rate"
          value={formatPct(stats.data?.win_rate ?? 0)}
          hint={`${stats.data?.wins ?? 0} / ${stats.data?.total ?? 0} сделок`}
          icon={Gauge}
          tone="olive"
        />
      </section>

      {/* Per-pair regime row */}
      {regime.data && regime.data.per_pair.length > 0 && (
        <section className="marble-card p-4">
          <div className="mb-3 flex items-baseline justify-between">
            <h3 className="display text-sm font-semibold">Состояние пар</h3>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              классификация по 4h
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {regime.data.per_pair.map((p) => (
              <RegimeBadge key={p.symbol} regime={p.regime} symbol={p.symbol} small />
            ))}
          </div>
        </section>
      )}

      <section className="marble-card overflow-hidden">
        <div className="flex items-baseline justify-between border-b border-hermes-gold/20 px-6 py-4">
          <h2 className="display text-xl font-semibold">Кривая equity</h2>
          <span className="text-xs uppercase tracking-wider text-muted-foreground">30 дней</span>
        </div>
        {equityHistory.data && equityHistory.data.length > 1 ? (
          <div className="px-3 py-3">
            <EquityChart history={equityHistory.data} />
          </div>
        ) : (
          <div className="grid h-72 place-items-center text-sm text-muted-foreground">
            <div className="text-center">
              <div className="font-serif text-2xl gold-text">Свиток ждёт первой записи</div>
              <p className="mt-2 max-w-md text-xs">
                График появится после нескольких циклов работы стратегии.
              </p>
            </div>
          </div>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="marble-card overflow-hidden">
          <div className="flex items-baseline justify-between border-b border-hermes-gold/20 px-5 py-3.5">
            <h3 className="display text-lg font-semibold">Открытые позиции</h3>
            <span className="text-xs uppercase tracking-wider text-muted-foreground">
              {positions.data?.length ?? 0} активных
            </span>
          </div>
          <PositionsTable positions={positions.data ?? []} loading={positions.isLoading} />
        </div>
        <KillSwitch />
      </section>
    </motion.div>
  );
}

function Kpi({
  label,
  value,
  hint,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  icon: typeof Coins;
  tone: "gold" | "success" | "warning" | "olive";
}) {
  const ring = {
    gold: "ring-hermes-gold/40 text-hermes-gold-deep",
    success: "ring-hermes-laurel/40 text-hermes-laurel",
    warning: "ring-hermes-bronze/40 text-hermes-bronze",
    olive: "ring-hermes-olive/40 text-hermes-olive",
  }[tone];
  return (
    <div className="marble-card p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
        <span className={`grid h-9 w-9 place-items-center rounded-full ring-1 ${ring} bg-card`}>
          <Icon size={16} />
        </span>
      </div>
      <div className="mt-3 number text-3xl font-semibold tracking-tight">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{hint}</div>
    </div>
  );
}

