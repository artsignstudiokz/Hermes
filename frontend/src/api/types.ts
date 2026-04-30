// Mirror of backend Pydantic schemas. Single source of typed truth on the FE.

export interface AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  profit: number;
  currency: string;
  leverage: number;
  server: string | null;
  login: number | null;
}

export interface Position {
  ticket: string;
  symbol: string;
  direction: "long" | "short";
  lot_size: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  swap: number;
  commission: number;
  opened_at: string;
}

export interface Trade {
  id: number;
  ticket: string;
  symbol: string;
  direction: string;
  level: number;
  lots: number;
  entry_price: number;
  exit_price: number | null;
  pnl: number;
  commission: number;
  swap: number;
  opened_at: string;
  closed_at: string | null;
  reason: string;
}

export interface Broker {
  id: number;
  type: "mt5" | "binance" | "bybit" | "okx";
  name: string;
  server: string | null;
  login: string | null;
  is_active: boolean;
  is_testnet: boolean;
}

export interface BrokerTestResult {
  ok: boolean;
  balance?: number;
  currency?: string;
  leverage?: number;
  server?: string;
  error?: string;
}

export interface StrategyParams {
  base_grid_distance_pips: number;
  grid_distance_multiplier: number;
  base_lot_size: number;
  lot_multiplier: number;
  max_grid_levels: number;
  fix_take_profit_pct: number;
  stop_drawdown_pct: number;
  max_portfolio_drawdown_pct: number;
  trend_filter_enabled: boolean;
  ema_fast: number;
  ema_slow: number;
  session_filter_enabled: boolean;
  risk_per_trade_pct: number;
  max_simultaneous_pairs: number;
  symbols: string[];
  timeframe: string;
}

export interface StrategyConfig {
  id: number;
  name: string;
  payload: StrategyParams;
  is_active: boolean;
  source: string;
}

export interface Preset {
  id: string;
  name: string;
  description: string;
  risk_emoji: string;
  payload: Partial<StrategyParams>;
}

export interface ValidationIssue {
  field: string;
  severity: "error" | "warning";
  message: string;
}

export interface ValidationResult {
  issues: ValidationIssue[];
  has_errors: boolean;
}

export interface TradingStatus {
  broker_account_id: number | null;
  worker: {
    running: boolean;
    paused: boolean;
    trading_enabled: boolean;
    last_tick: string | null;
    tick_count: number;
    last_error: string | null;
  } | null;
}

export interface ManualOrderInput {
  symbol: string;
  direction: "long" | "short";
  lot_size: number;
  comment?: string;
}

export interface ManualOrderResult {
  ticket: string;
  symbol: string;
  direction: string;
  lot_size: number;
  entry_price: number | null;
}

export interface TradeStats {
  total: number;
  wins: number;
  win_rate: number;
  pnl_total: number;
  commission_total: number;
}

export interface EquityPoint {
  ts: string;
  equity: number;
  balance: number;
  drawdown_pct: number;
}
