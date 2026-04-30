import { motion } from "framer-motion";
import { Activity, ArrowUpRight, Coins, FlaskConical, Pause, Play, Power, ShieldAlert, TrendingUp, Zap, ZapOff } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAccount, useEquityHistory, useTradingStatus } from "@/api/useAccount";
import { useBrokers } from "@/api/useBrokers";
import { usePositions } from "@/api/usePositions";
import { useTradeStats } from "@/api/useTrades";
import {
  useDisableTrading,
  useEnableTrading,
  usePauseTrading,
  useResumeTrading,
  useStartTrading,
  useStopTrading,
  useTestOrder,
} from "@/api/useTrading";
import { useStrategyConfig } from "@/api/useStrategy";
import { useRegime } from "@/api/useAdaptive";
import { ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";
import { EquityChart } from "@/components/charts/EquityChart";
import { RegimeBadge } from "@/components/charts/RegimeBadge";
import { PositionsTable } from "@/components/tables/PositionsTable";
import { BalanceCard } from "@/components/widgets/BalanceCard";
import { BotStatusBadge } from "@/components/widgets/BotStatusBadge";
import { KillSwitch } from "@/components/widgets/KillSwitch";
import { KpiCard } from "@/components/widgets/KpiCard";
import { PageHeader } from "@/components/widgets/PageHeader";
import { RiskGauge } from "@/components/widgets/RiskGauge";
import { SignalToasts } from "@/components/widgets/SignalToast";
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
  const enableTrading = useEnableTrading();
  const disableTrading = useDisableTrading();
  const testOrder = useTestOrder();
  const [testBusy, setTestBusy] = useState(false);

  const running = status.data?.worker?.running ?? false;
  const paused = status.data?.worker?.paused ?? false;
  const tradingOn = status.data?.worker?.trading_enabled ?? false;

  const stopPct = (config.data?.payload?.stop_drawdown_pct ?? 10) / 100;
  const hardPct = (config.data?.payload?.max_portfolio_drawdown_pct ?? 20) / 100;

  const peakEquity = (equityHistory.data ?? []).reduce(
    (m, p) => Math.max(m, p.equity),
    account.data?.equity ?? 0,
  );
  const drawdown = peakEquity > 0 && account.data
    ? Math.max(0, (peakEquity - account.data.equity) / peakEquity)
    : 0;

  const winRateSpark = (equityHistory.data ?? []).slice(-30).map((p) => p.equity);

  const onPrimary = () => {
    if (!activeBroker) return;
    if (!running) start.mutate(activeBroker.id);
    else if (paused) resume.mutate();
    else pause.mutate();
  };

  const primaryLabel = !running ? "Запустить" : paused ? "Возобновить" : "Пауза";
  const PrimaryIcon = !running ? Power : paused ? Play : Pause;

  const onToggleTrading = async () => {
    try {
      if (tradingOn) await disableTrading.mutateAsync();
      else await enableTrading.mutateAsync();
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : err instanceof Error ? err.message : String(err);
      toast.error("Не удалось переключить торговлю", detail);
    }
  };

  const onTestOrder = async () => {
    if (!activeBroker) return;
    const symbol = config.data?.payload.symbols?.[0] ?? "EURUSD";
    setTestBusy(true);
    try {
      const r = await testOrder.mutateAsync({
        symbol, direction: "long", lot_size: 0.01, comment: "manual_test",
      });
      toast.success("Тестовая сделка открыта", `${r.symbol} long 0.01 · ticket ${r.ticket}`);
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : err instanceof Error ? err.message : String(err);
      toast.error("Тест не удался", detail);
    } finally {
      setTestBusy(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8"
    >
      <SignalToasts />

      <PageHeader
        eyebrow="Олимп"
        title={
          activeBroker ? (
            <>Счёт <span className="gold-text">{activeBroker.name}</span></>
          ) : (
            <>Подключите <span className="gold-text">брокера</span></>
          )
        }
        subtitle="«Нет дома богаче того, в котором живёт Гермес — посланник прибыли.»"
        status={
          <div className="flex items-center gap-2">
            <BotStatusBadge />
            {regime.data && regime.data.per_pair.length > 0 && (
              <RegimeBadge
                regime={regime.data.regime}
                confidence={regime.data.per_pair[0]?.confidence ?? 0}
              />
            )}
          </div>
        }
        actions={
          !activeBroker ? (
            <Link
              to="/brokers"
              className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold uppercase tracking-wider"
            >
              Подключить брокера <ArrowUpRight size={14} />
            </Link>
          ) : (
            <>
              <button
                onClick={onPrimary}
                disabled={start.isPending || pause.isPending || resume.isPending}
                className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
              >
                <PrimaryIcon size={16} /> {primaryLabel}
              </button>
              {running && (
                <>
                  <button
                    onClick={onToggleTrading}
                    disabled={enableTrading.isPending || disableTrading.isPending}
                    title={tradingOn
                      ? "Бот сейчас открывает реальные сделки. Нажмите чтобы вернуться в режим наблюдения."
                      : "Бот наблюдает за рынком, но не торгует. Нажмите чтобы разрешить открытие реальных сделок."}
                    className={`inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold uppercase tracking-wider transition disabled:opacity-50 ${
                      tradingOn
                        ? "border border-hermes-laurel/50 bg-hermes-laurel/15 text-hermes-laurel hover:bg-hermes-laurel/25"
                        : "border border-hermes-gold/40 bg-hermes-alabaster text-muted-foreground hover:bg-hermes-parchment"
                    }`}
                  >
                    {tradingOn ? <Zap size={14} /> : <ZapOff size={14} />}
                    {tradingOn ? "Торговля: ВКЛ" : "Только наблюдение"}
                  </button>
                  <button
                    onClick={onTestOrder}
                    disabled={testBusy}
                    title="Открыть пробную сделку 0.01 лота для проверки соединения с брокером."
                    className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-3 text-sm font-medium hover:bg-hermes-parchment transition disabled:opacity-50"
                  >
                    <FlaskConical size={14} /> Тест-сделка
                  </button>
                  <button
                    onClick={() => stop.mutate()}
                    disabled={stop.isPending}
                    className="rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-3 text-sm font-medium hover:bg-hermes-parchment transition"
                  >
                    Остановить
                  </button>
                </>
              )}
            </>
          )
        }
      />

      {/* Top section: BalanceCard (wide) + 2 KPIs */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <BalanceCard
          account={account.data}
          loading={account.isLoading}
          history={equityHistory.data}
        />
        <KpiCard
          label="P&L · 30 дней"
          value={formatMoney(stats.data?.pnl_total ?? 0)}
          hint={`${stats.data?.total ?? 0} сделок`}
          delta={
            stats.data && stats.data.pnl_total !== 0
              ? {
                  text: formatPct(stats.data.pnl_total / Math.max(1, account.data?.balance ?? 10000)),
                  positive: stats.data.pnl_total > 0,
                }
              : undefined
          }
          icon={TrendingUp}
          tone="laurel"
          sparkline={winRateSpark}
        />
        <KpiCard
          label="Win-rate"
          value={formatPct(stats.data?.win_rate ?? 0)}
          hint={`${stats.data?.wins ?? 0} / ${stats.data?.total ?? 0}`}
          icon={Activity}
          tone="aegean"
        />
      </section>

      {/* Risk + Per-pair regimes */}
      <section className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <RiskGauge drawdown={drawdown} stop={stopPct} hardStop={hardPct} />

        {regime.data && regime.data.per_pair.length > 0 ? (
          <div className="marble-card p-5">
            <div className="mb-4 flex items-baseline justify-between">
              <h3 className="display text-base font-semibold text-hermes-navy">
                Состояние пар <span className="text-muted-foreground font-normal text-xs">· 4h</span>
              </h3>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                {regime.data.per_pair.length} пар
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {regime.data.per_pair.map((p) => (
                <RegimeBadge
                  key={p.symbol}
                  regime={p.regime}
                  symbol={p.symbol}
                  confidence={p.confidence}
                />
              ))}
            </div>
          </div>
        ) : (
          <div className="marble-card grid place-items-center p-5 text-center">
            <p className="font-serif italic text-sm text-muted-foreground">
              Регимы появятся когда Hermes увидит первые тики.
            </p>
          </div>
        )}
      </section>

      {/* Equity chart */}
      <section className="marble-card overflow-hidden">
        <div className="flex items-baseline justify-between border-b border-hermes-gold/20 px-6 py-4">
          <div>
            <h2 className="display text-xl font-semibold text-hermes-navy">Кривая equity</h2>
            <p className="mt-0.5 text-[11px] text-muted-foreground">Live · WebSocket</p>
          </div>
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

      {/* Positions + Kill switch */}
      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="marble-card overflow-hidden">
          <div className="flex items-baseline justify-between border-b border-hermes-gold/20 px-5 py-3.5">
            <div>
              <h3 className="display text-lg font-semibold text-hermes-navy">Открытые позиции</h3>
              <p className="mt-0.5 text-[11px] text-muted-foreground">Обновляется в реальном времени</p>
            </div>
            <span className="rounded-full bg-hermes-gold/15 px-2.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-hermes-gold-deep">
              {positions.data?.length ?? 0} активных
            </span>
          </div>
          <PositionsTable positions={positions.data ?? []} loading={positions.isLoading} />
        </div>
        <KillSwitch />
      </section>

      {/* Footer KPI strip — Sharpe, Coins, Bot uptime */}
      <section className="marble-card flex flex-wrap items-center justify-around gap-6 px-6 py-4 text-xs uppercase tracking-[0.18em] text-muted-foreground">
        <span className="flex items-center gap-2">
          <Coins size={13} className="text-hermes-gold-deep" />
          Стратегия: {config.data?.name ?? "—"}
        </span>
        <span className="flex items-center gap-2">
          <ShieldAlert size={13} className="text-hermes-bronze" />
          Stop: {(stopPct * 100).toFixed(0)}% · Max: {(hardPct * 100).toFixed(0)}%
        </span>
        <span className="flex items-center gap-2">
          <Activity size={13} className="text-hermes-laurel" />
          Тиков: <span className="number text-foreground">{status.data?.worker?.tick_count ?? 0}</span>
        </span>
      </section>
    </motion.div>
  );
}
