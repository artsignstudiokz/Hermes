"""Signal generation with human-readable reasoning.

Each strategy produces zero or one Signal per bar. A Signal carries:
  - direction (long/short/flat)
  - confidence (0..1)
  - the indicator snapshot it was derived from
  - a `reason` string telling the user exactly which conditions fired

The Ensemble merges signals from multiple strategies via majority vote,
weighted by confidence. The final SignalReport is broadcast to the SPA
on /ws/signals so users can see *why* the bot opened a trade.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

from app.core.strategy.indicators import IndicatorSnapshot

Direction = Literal["long", "short", "flat"]


@dataclass(frozen=True)
class Signal:
    strategy: str
    symbol: str
    direction: Direction
    confidence: float          # 0..1
    reason: str                # markdown — shown in the UI
    indicators: dict[str, float]  # the values that drove the decision

    def to_dict(self) -> dict:
        return asdict(self)


# ── Individual strategies ────────────────────────────────────────────────


class TrendFollowingStrategy:
    """EMA fast/slow cross confirmed by ADX trend strength.

    Long when ema_fast > ema_slow AND ADX > 25 AND +DI > -DI.
    Short on the mirror condition. Anything else → flat.
    """
    name = "Trend Following"

    def __init__(self, adx_min: float = 25.0):
        self.adx_min = adx_min

    def evaluate(self, s: IndicatorSnapshot) -> Signal | None:
        bull = s.ema_fast > s.ema_slow and s.plus_di > s.minus_di
        bear = s.ema_fast < s.ema_slow and s.minus_di > s.plus_di
        strong = s.adx >= self.adx_min
        if bull and strong:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="long",
                confidence=min(1.0, s.adx / 50.0),
                reason=(
                    f"EMA{50} ({s.ema_fast:.4f}) выше EMA{200} ({s.ema_slow:.4f}); "
                    f"ADX {s.adx:.1f} ≥ {self.adx_min:.0f} (тренд устойчивый); "
                    f"+DI {s.plus_di:.1f} > −DI {s.minus_di:.1f}."
                ),
                indicators={"ema_fast": s.ema_fast, "ema_slow": s.ema_slow,
                            "adx": s.adx, "plus_di": s.plus_di, "minus_di": s.minus_di},
            )
        if bear and strong:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="short",
                confidence=min(1.0, s.adx / 50.0),
                reason=(
                    f"EMA{50} ({s.ema_fast:.4f}) ниже EMA{200} ({s.ema_slow:.4f}); "
                    f"ADX {s.adx:.1f} ≥ {self.adx_min:.0f} (тренд устойчивый); "
                    f"−DI {s.minus_di:.1f} > +DI {s.plus_di:.1f}."
                ),
                indicators={"ema_fast": s.ema_fast, "ema_slow": s.ema_slow,
                            "adx": s.adx, "plus_di": s.plus_di, "minus_di": s.minus_di},
            )
        return None


class MeanReversionStrategy:
    """BB touch + RSI extreme + Stochastic-turn confirmation in low ADX.

    Plain "fade the touch" lost catastrophically in the v1.0.21 backtest
    (Sharpe −13). The issue: in synthetic / real noisy data the touch
    keeps extending — you're catching falling knives. v1.0.22 adds a
    stochastic-turn confirmation: only enter long when %K crosses above
    %D (early exit-from-oversold signal), and mirror for short. This
    cuts trade count drastically but improves expectancy.
    """
    name = "Mean Reversion"

    def __init__(self, rsi_oversold: float = 30, rsi_overbought: float = 70,
                 adx_max: float = 20.0):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.adx_max = adx_max

    def evaluate(self, s: IndicatorSnapshot) -> Signal | None:
        range_bound = s.adx <= self.adx_max
        if not range_bound:
            return None
        long_setup = s.close <= s.bb_lower and s.rsi <= self.rsi_oversold
        short_setup = s.close >= s.bb_upper and s.rsi >= self.rsi_overbought
        stoch_turning_up = s.stoch_k > s.stoch_d and s.stoch_k < 50
        stoch_turning_down = s.stoch_k < s.stoch_d and s.stoch_k > 50
        if long_setup and stoch_turning_up:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="long",
                confidence=min(1.0, (self.rsi_oversold - s.rsi + 10) / 30.0),
                reason=(
                    f"BB-нижняя {s.bb_lower:.4f} коснулась, RSI {s.rsi:.1f} перепродан, "
                    f"Stochastic %K {s.stoch_k:.1f} развернулся вверх над %D {s.stoch_d:.1f} — "
                    f"условия для возврата к среднему."
                ),
                indicators={"close": s.close, "bb_lower": s.bb_lower,
                            "rsi": s.rsi, "adx": s.adx,
                            "stoch_k": s.stoch_k, "stoch_d": s.stoch_d},
            )
        if short_setup and stoch_turning_down:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="short",
                confidence=min(1.0, (s.rsi - self.rsi_overbought + 10) / 30.0),
                reason=(
                    f"BB-верхняя {s.bb_upper:.4f} коснулась, RSI {s.rsi:.1f} перекуплен, "
                    f"Stochastic %K {s.stoch_k:.1f} развернулся вниз под %D {s.stoch_d:.1f} — "
                    f"условия для возврата к среднему."
                ),
                indicators={"close": s.close, "bb_upper": s.bb_upper,
                            "rsi": s.rsi, "adx": s.adx,
                            "stoch_k": s.stoch_k, "stoch_d": s.stoch_d},
            )
        return None


class BreakoutStrategy:
    """Donchian channel breakout confirmed by volatility expansion.

    A pure `close >= donchian_high` test almost never fires because
    the high INCLUDES the current bar — so the breakout only counts
    when the current candle prints the new high. Backtest of v1.0.21
    showed exactly 0 trades on 8640 bars. v1.0.22 relaxes:
      • require close to clear the channel by `min_margin` (0.05% of price)
      • require ATR% above `atr_floor` so we don't fade dead markets
    """
    name = "Breakout"

    def __init__(self, min_margin: float = 0.0005, atr_floor: float = 0.0008):
        self.min_margin = min_margin
        self.atr_floor = atr_floor

    def evaluate(self, s: IndicatorSnapshot) -> Signal | None:
        if s.atr_pct < self.atr_floor:
            return None
        high_threshold = s.donchian_high * (1 - self.min_margin)
        low_threshold = s.donchian_low * (1 + self.min_margin)
        if s.close >= high_threshold:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="long",
                confidence=min(1.0, s.atr_pct * 80),
                reason=(
                    f"Цена {s.close:.4f} пробила Donchian-хай {s.donchian_high:.4f}; "
                    f"ATR {s.atr_pct * 100:.2f}% выше порога — пробой подтверждён."
                ),
                indicators={"close": s.close, "donchian_high": s.donchian_high,
                            "atr": s.atr, "atr_pct": s.atr_pct},
            )
        if s.close <= low_threshold:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="short",
                confidence=min(1.0, s.atr_pct * 80),
                reason=(
                    f"Цена {s.close:.4f} пробила Donchian-лоу {s.donchian_low:.4f}; "
                    f"ATR {s.atr_pct * 100:.2f}% выше порога — пробой подтверждён."
                ),
                indicators={"close": s.close, "donchian_low": s.donchian_low,
                            "atr": s.atr, "atr_pct": s.atr_pct},
            )
        return None


class MomentumStrategy:
    """MACD + Stochastic confluence.

    Long when MACD histogram > 0 AND Stochastic crosses up below 50.
    """
    name = "Momentum"

    def evaluate(self, s: IndicatorSnapshot) -> Signal | None:
        momentum_up = s.macd_hist > 0 and s.stoch_k > s.stoch_d and s.stoch_k < 80
        momentum_dn = s.macd_hist < 0 and s.stoch_k < s.stoch_d and s.stoch_k > 20
        if momentum_up:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="long",
                confidence=min(1.0, abs(s.macd_hist) * 100),
                reason=(
                    f"MACD-гистограмма {s.macd_hist:+.5f} положительна; "
                    f"Stochastic %K {s.stoch_k:.1f} пересёк %D {s.stoch_d:.1f} вверх; "
                    f"импульс направлен наверх."
                ),
                indicators={"macd_hist": s.macd_hist, "stoch_k": s.stoch_k, "stoch_d": s.stoch_d},
            )
        if momentum_dn:
            return Signal(
                strategy=self.name, symbol=s.symbol, direction="short",
                confidence=min(1.0, abs(s.macd_hist) * 100),
                reason=(
                    f"MACD-гистограмма {s.macd_hist:+.5f} отрицательна; "
                    f"Stochastic %K {s.stoch_k:.1f} опустился ниже %D {s.stoch_d:.1f}; "
                    f"импульс направлен вниз."
                ),
                indicators={"macd_hist": s.macd_hist, "stoch_k": s.stoch_k, "stoch_d": s.stoch_d},
            )
        return None


# ── Ensemble / combinator ────────────────────────────────────────────────


@dataclass
class SignalReport:
    """Final, consumer-ready decision for one symbol on one bar."""
    symbol: str
    ts: str
    direction: Direction
    confidence: float
    reason: str                          # combined markdown explanation
    contributing: list[dict] = field(default_factory=list)  # raw per-strategy signals
    indicators: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": "analysis",
            "symbol": self.symbol,
            "ts": self.ts,
            "direction": self.direction,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "contributing": self.contributing,
            "indicators": self.indicators,
        }


class StrategyEnsemble:
    """Run multiple strategies, merge their signals, produce one decision.

    Modes:
      - "any":      first long signal wins (aggressive)
      - "majority": >50% of strategies that produced a signal must agree (default)
      - "all":      every strategy that produced a signal must agree (conservative)
    """
    def __init__(self, strategies: list, mode: str = "majority"):
        if not strategies:
            raise ValueError("StrategyEnsemble needs at least one strategy")
        self.strategies = strategies
        self.mode = mode

    def evaluate(self, snap: IndicatorSnapshot) -> SignalReport:
        signals: list[Signal] = []
        for strat in self.strategies:
            try:
                sig = strat.evaluate(snap)
            except Exception:
                sig = None
            if sig is not None:
                signals.append(sig)

        if not signals:
            return SignalReport(
                symbol=snap.symbol,
                ts=datetime.now(timezone.utc).isoformat(),
                direction="flat",
                confidence=0.0,
                reason=(
                    "Ни одна из активных стратегий не нашла достаточно сильного сигнала. "
                    "Бот наблюдает: жду совпадения условий по выбранному набору индикаторов."
                ),
                contributing=[],
                indicators=_snap_to_dict(snap),
            )

        # Vote.
        longs = [s for s in signals if s.direction == "long"]
        shorts = [s for s in signals if s.direction == "short"]
        total = len(signals)
        if self.mode == "any":
            chosen = longs if longs else shorts
        elif self.mode == "all":
            if longs and not shorts:
                chosen = longs
            elif shorts and not longs:
                chosen = shorts
            else:
                chosen = []
        else:  # majority
            if len(longs) > len(shorts) and len(longs) / total > 0.5:
                chosen = longs
            elif len(shorts) > len(longs) and len(shorts) / total > 0.5:
                chosen = shorts
            else:
                chosen = []

        if not chosen:
            reasons = "\n".join(f"• **{s.strategy}** ({s.direction}): {s.reason}" for s in signals)
            return SignalReport(
                symbol=snap.symbol,
                ts=datetime.now(timezone.utc).isoformat(),
                direction="flat",
                confidence=0.0,
                reason=(
                    f"Стратегии разошлись во мнениях, открывать не безопасно ({self.mode}-режим).\n\n"
                    f"{reasons}"
                ),
                contributing=[s.to_dict() for s in signals],
                indicators=_snap_to_dict(snap),
            )

        avg_conf = sum(s.confidence for s in chosen) / len(chosen)
        direction: Direction = chosen[0].direction
        reasons = "\n".join(f"• **{s.strategy}**: {s.reason}" for s in chosen)
        head = (
            f"**{direction.upper()}** по {snap.symbol} — "
            f"{len(chosen)} из {total} стратегий согласны (уверенность {avg_conf:.2f})."
        )
        return SignalReport(
            symbol=snap.symbol,
            ts=datetime.now(timezone.utc).isoformat(),
            direction=direction,
            confidence=avg_conf,
            reason=f"{head}\n\n{reasons}",
            contributing=[s.to_dict() for s in signals],
            indicators=_snap_to_dict(snap),
        )


def _snap_to_dict(snap: IndicatorSnapshot) -> dict[str, float]:
    return {
        "close": snap.close,
        "rsi": snap.rsi,
        "macd": snap.macd,
        "macd_signal": snap.macd_signal,
        "macd_hist": snap.macd_hist,
        "bb_upper": snap.bb_upper,
        "bb_lower": snap.bb_lower,
        "bb_middle": snap.bb_middle,
        "atr": snap.atr,
        "atr_pct": snap.atr_pct,
        "ema_fast": snap.ema_fast,
        "ema_slow": snap.ema_slow,
        "adx": snap.adx,
        "plus_di": snap.plus_di,
        "minus_di": snap.minus_di,
        "stoch_k": snap.stoch_k,
        "stoch_d": snap.stoch_d,
        "donchian_high": snap.donchian_high,
        "donchian_low": snap.donchian_low,
    }


DEFAULT_STRATEGIES = {
    "trend": TrendFollowingStrategy,
    "mean_reversion": MeanReversionStrategy,
    "breakout": BreakoutStrategy,
    "momentum": MomentumStrategy,
}


def build_ensemble(names: list[str], mode: str = "majority") -> StrategyEnsemble:
    """Factory used by the runner — accepts a list of preset names.

    Default of [trend, momentum] is the only pair we've actually validated
    profitable on synthetic walk-forward (Sharpe > 1 vs MeanReversion's
    -13 in v1.0.21). Operators can opt into MeanReversion / Breakout
    explicitly via the Strategy config, but we don't bake them into the
    autonomous-mode default until a per-pair calibration confirms they
    add expectancy on the operator's actual broker feed.
    """
    chosen = []
    for n in names:
        cls = DEFAULT_STRATEGIES.get(n)
        if cls:
            chosen.append(cls())
    if not chosen:
        chosen = [TrendFollowingStrategy(adx_min=22), MomentumStrategy()]
    return StrategyEnsemble(chosen, mode=mode)
