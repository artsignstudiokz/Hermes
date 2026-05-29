import { useEffect, useRef, useState } from "react";
import {
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type Time,
  createChart,
} from "lightweight-charts";

import { subscribe } from "@/lib/ws";

interface Point {
  ts: string;
  equity: number;
}

interface Props {
  history: Point[];
  height?: number;
}

/** Live equity curve in the spirit of TradingView, themed for Hermes.
 *
 * v1.0.34: every lightweight-charts call is wrapped in try/catch. The
 * library does its own WebGL/Canvas init at createChart time, which on
 * some WebView2 / GPU-driver combos throws a native exception that
 * tears down the renderer process. We log the error and fall back to a
 * "chart unavailable" placeholder so the rest of the Dashboard stays
 * up. setData / update also validate inputs (sorted, deduped, finite)
 * because lightweight-charts will throw if timestamps aren't strictly
 * ascending - which used to crash the renderer.
 */
export function EquityChart({ history, height = 280 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    let chart: IChartApi | null = null;
    try {
      chart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#5b5046",
          fontFamily: "JetBrains Mono, ui-monospace, monospace",
        },
        grid: {
          vertLines: { color: "rgba(168, 136, 79, 0.08)" },
          horzLines: { color: "rgba(168, 136, 79, 0.10)" },
        },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
        crosshair: { vertLine: { color: "#A8884F" }, horzLine: { color: "#A8884F" } },
        autoSize: true,
      });
      const series = chart.addAreaSeries({
        lineColor: "#A8884F",
        topColor: "rgba(201, 169, 110, 0.45)",
        bottomColor: "rgba(201, 169, 110, 0)",
        lineWidth: 2,
        priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      });
      chartRef.current = chart;
      seriesRef.current = series;
    } catch (e) {
      console.error("EquityChart createChart failed:", e);
      setFailed(true);
    }
    return () => {
      try { chart?.remove(); } catch { /* ignore */ }
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    try {
      // Sanitise: drop NaN/Infinity equity values, parse timestamps,
      // sort ascending, dedupe identical times. lightweight-charts
      // throws if any of these conditions are violated, and on some
      // WebView2 builds the throw kills the renderer process.
      const seen = new Set<number>();
      const data: { time: Time; value: number }[] = [];
      for (const p of history) {
        const t = Math.floor(new Date(p.ts).getTime() / 1000);
        if (!Number.isFinite(t) || !Number.isFinite(p.equity)) continue;
        if (seen.has(t)) continue;
        seen.add(t);
        data.push({ time: t as Time, value: p.equity });
      }
      data.sort((a, b) => (a.time as number) - (b.time as number));
      seriesRef.current.setData(data);
      chartRef.current?.timeScale().fitContent();
    } catch (e) {
      console.error("EquityChart setData failed:", e);
    }
  }, [history]);

  useEffect(() => {
    return subscribe<{ ts: string; equity: number }>("equity", (msg) => {
      try {
        const t = Math.floor(new Date(msg.ts).getTime() / 1000);
        if (!Number.isFinite(t) || !Number.isFinite(msg.equity)) return;
        seriesRef.current?.update({ time: t as Time, value: msg.equity });
      } catch (e) {
        console.error("EquityChart update failed:", e);
      }
    });
  }, []);

  if (failed) {
    return (
      <div
        style={{ width: "100%", height }}
        className="grid place-items-center text-xs text-muted-foreground"
      >
        График временно недоступен. Данные сохраняются.
      </div>
    );
  }

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}
