import { useMemo } from "react";

interface Props {
  values: number[];
  width?: number;
  height?: number;
  stroke?: string;
  fillFrom?: string;
  fillTo?: string;
  className?: string;
}

/** Inline SVG sparkline — used inside KPI cards. */
export function MiniSparkline({
  values,
  width = 120,
  height = 36,
  stroke = "#A8884F",
  fillFrom = "rgba(201,169,110,0.35)",
  fillTo = "rgba(201,169,110,0)",
  className,
}: Props) {
  const { d, dArea, lastY } = useMemo(() => {
    if (values.length < 2) return { d: "", dArea: "", lastY: height };
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const stepX = width / (values.length - 1);
    const points = values.map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return [x, y] as const;
    });
    const path = points
      .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`)
      .join(" ");
    const area =
      `M${points[0][0].toFixed(2)} ${height} ` +
      points.map(([x, y]) => `L${x.toFixed(2)} ${y.toFixed(2)}`).join(" ") +
      ` L${points[points.length - 1][0].toFixed(2)} ${height} Z`;
    return { d: path, dArea: area, lastY: points[points.length - 1][1] };
  }, [values, width, height]);

  if (values.length < 2) return null;

  const gradId = `sparkline-grad-${Math.random().toString(36).slice(2, 8)}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={fillFrom} />
          <stop offset="100%" stopColor={fillTo} />
        </linearGradient>
      </defs>
      <path d={dArea} fill={`url(#${gradId})`} />
      <path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={width - 1} cy={lastY} r={2.4} fill={stroke} />
    </svg>
  );
}
