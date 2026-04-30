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

export function formatMoney(n: number | null | undefined, currency: string = "USD"): string {
  const v = n ?? 0;
  const sign = v < 0 ? "−" : "";
  const symbol = currency === "USD" ? "$" : "";
  return `${sign}${symbol}${moneyFmt.format(Math.abs(v))}`;
}

export function formatCompact(n: number | null | undefined): string {
  return compactFmt.format(n ?? 0);
}

export function formatPct(ratio: number | null | undefined): string {
  return pctFmt.format(ratio ?? 0);
}

export function formatPips(pips: number | null | undefined): string {
  return `${(pips ?? 0).toFixed(1)} п.`;
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
