import { useEffect, useRef } from "react";
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

/** Live equity curve in the spirit of TradingView, themed for Hermes. */
export function EquityChart({ history, height = 280 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  // Init chart once.
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
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
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Hydrate series from history prop.
  useEffect(() => {
    if (!seriesRef.current) return;
    const data = history.map((p) => ({
      time: Math.floor(new Date(p.ts).getTime() / 1000) as Time,
      value: p.equity,
    }));
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [history]);

  // Live updates from /ws/equity.
  useEffect(() => {
    return subscribe<{ ts: string; equity: number }>("equity", (msg) => {
      seriesRef.current?.update({
        time: Math.floor(new Date(msg.ts).getTime() / 1000) as Time,
        value: msg.equity,
      });
    });
  }, []);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}
