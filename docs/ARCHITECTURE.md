# Hermes — Architecture

## Stack

| Layer | Tech |
|---|---|
| **Desktop wrapper** | PyWebView (Edge WebView2 / WKWebView) — single process |
| **Backend** | FastAPI 0.115 + SQLAlchemy 2 async + aiosqlite |
| **Frontend** | React 18 + Vite + TypeScript + Tailwind + shadcn/ui |
| **Charts** | lightweight-charts (TradingView-style) |
| **Brokers** | MetaTrader5 SDK + ccxt async (Binance / Bybit / OKX) |
| **ML** | Optuna + scipy + pandas |
| **Security** | argon2-cffi + cryptography (Fernet AES-128) |
| **Notifications** | pywebpush + py_vapid + httpx (Telegram) |
| **Tunnel** | pyngrok |
| **Scheduler** | APScheduler (asyncio) |
| **Packaging** | PyInstaller + Inno Setup (Win) / pkgbuild (macOS) |

## Process diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Native Desktop Window (PyWebView, frameless)                    │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Custom title bar (React)         _ □ ✕                     │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ React App                                                   │ │
│ │   • TanStack Query — server cache + WS invalidation         │ │
│ │   • Zustand — UI/auth state                                 │ │
│ │   • lightweight-charts — equity curve                       │ │
│ │   • Framer Motion — page/element transitions                │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/WS over 127.0.0.1:<ephemeral>
┌─────────────────────▼───────────────────────────────────────────┐
│ FastAPI (single asyncio loop)                                    │
│  • REST  /api/{auth,brokers,account,positions,trades,strategy,   │
│           trading,onboarding,notifications,tunnel,adaptive,       │
│           backtest,optimize,system}                              │
│  • WS    /ws/{positions,equity,signals,logs,prices,system,       │
│              calibration,backtest_<id>,optimize_<id>}            │
│                                                                  │
│  Middleware: CORS (loopback only) + JWT (process-local secret)   │
│                                                                  │
│  ┌──── Services ────────────────────────────────────────────┐   │
│  │ TradingService    BacktestService    OptimizeService     │   │
│  │ AccountService    NotificationService TunnelService      │   │
│  │ OnboardingService                                         │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──── Workers ─────────────────────────────────────────────┐   │
│  │ trading_worker — strategy tick loop, persists snapshots   │   │
│  │ APScheduler   — cron Sun 03:00 calibration + heartbeat    │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──── Core ────────────────────────────────────────────────┐   │
│  │ brokers/   BrokerAdapter (ABC) → MT5Adapter, CCXTAdapter  │   │
│  │ strategy/  Runner (wraps legacy GridStrategy) + presets    │   │
│  │ adaptive/  RegimeDetector + AutoCalibrator + Policy        │   │
│  │ security/  CredentialVault (Argon2id+Fernet) + JWT         │   │
│  │ notif/     Telegram + WebPush + templates                  │   │
│  │ tunnel/    NgrokTunnel + QR generator                      │   │
│  │ scheduler/ APScheduler bootstrap                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Storage:                                                        │
│   data/app.db          (SQLite WAL — broker_accounts,            │
│                         strategy_configs, trades, equity_points, │
│                         calibration_runs, …)                     │
│   data/credentials.enc (Fernet-encrypted creds)                  │
│   data/vapid.json      (Web Push keypair)                        │
│   data/data_cache/     (OHLCV cache for backtest)                │
└──────────────────────────────────────────────────────────────────┘
```

## Single-process design

PyWebView and FastAPI live in the same Python process. The webview is created
on the main thread; uvicorn runs in a daemon thread. MetaTrader5 imports lazily
when an MT5 broker is added — so macOS builds don't crash on import even though
the SDK is Windows-only.

## Storage paths

Resolved via `platformdirs`:

| OS | Data dir |
|---|---|
| Windows | `%APPDATA%\Hermes` |
| macOS | `~/Library/Application Support/Hermes` |
| Linux | `~/.local/share/Hermes` |

## Phase boundaries (build history)

- **Phase 1** — Foundation: vault, JWT, settings, PyWebView shell, React skeleton, Hermes branding.
- **Phase 2** — Core trading: BrokerAdapter ABC, MT5Adapter, StrategyRunner, TradingService + worker, WS broadcasts, REST routes.
- **Phase 3** — Onboarding wizard, MT5 server autodetect, ngrok tunnel + QR + PIN, Web Push (VAPID), Telegram refactor, NotificationService.
- **Phase 4** — Crypto: full CCXTAdapter. Adaptive: RegimeDetector + walk-forward + AutoCalibrator (champion-challenger) + APScheduler. Backtest + Optimize services with WS progress.
- **Phase 5** — Real logo + favicon integration, icon generation pipeline, PyInstaller spec hardening, macOS .app + .pkg builders, Inno Setup polish, smoke test, user guide.
- **Phase 6** — Tests + auto-update + final QA (planned).

## Security model

- **Master password** never leaves memory. Argon2id derives a 32-byte key; Fernet encrypts the credentials JSON.
- **Backend bind**: `127.0.0.1:<ephemeral>`, never wildcard.
- **JWT** signed with `os.urandom(32)` per process — restart = log-out (intentional for a desktop app).
- **Tunnel**: ngrok URL + 6-digit PIN (rotates every 24h, 5-fail lockout = 10min).
- **Validation guard**: strategy cannot save params requiring > 50% deposit margin.
- **CORS**: regex `^https?://(127\.0\.0\.1|localhost)(:\d+)?$` only.

## Failure modes

- **Backend crash**: PyWebView shows a marble error page (handled in `App.tsx` boot retry).
- **Worker exception**: caught in `trading_worker._run`, broadcast as `signals.error`, loop continues with next tick.
- **Vault locked at restart**: user must enter master password. Auto-trading does NOT auto-resume — explicit action required.
- **Adapter disconnect**: `BrokerRegistry` re-`connect()` is idempotent; trading service will surface error and pause the worker.
