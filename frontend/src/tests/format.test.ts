import { describe, expect, it } from "vitest";

import { formatMoney, formatPct, formatPips, formatCompact } from "@/lib/format";

describe("format helpers", () => {
  it("formats money with sign and currency symbol", () => {
    expect(formatMoney(1234.56)).toMatch(/\$1[\s ]?234,56/);
    expect(formatMoney(-50.5)).toContain("−");
  });

  it("formats percent ratios", () => {
    expect(formatPct(0.123)).toMatch(/12,30/);
    expect(formatPct(-0.05)).toMatch(/−|-/);
  });

  it("formats pips with one decimal", () => {
    expect(formatPips(12.345)).toBe("12.3 п.");
  });

  it("formats compact numbers", () => {
    const out = formatCompact(15_000);
    expect(out.length).toBeLessThanOrEqual(8);
    expect(out).toMatch(/15/);
  });
});
