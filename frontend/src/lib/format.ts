/**
 * Number/date formatting helpers. Locale defaults to ru-RU.
 */

const moneyFmt = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactFmt = new Intl.NumberFormat("ru-RU", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const pctFmt = new Intl.NumberFormat("ru-RU", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatMoney(n: number, currency: string = "USD"): string {
  const sign = n < 0 ? "−" : "";
  const symbol = currency === "USD" ? "$" : "";
  return `${sign}${symbol}${moneyFmt.format(Math.abs(n))}`;
}

export function formatCompact(n: number): string {
  return compactFmt.format(n);
}

export function formatPct(ratio: number): string {
  return pctFmt.format(ratio);
}

export function formatPips(pips: number): string {
  return `${pips.toFixed(1)} п.`;
}

export function formatDateTime(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
