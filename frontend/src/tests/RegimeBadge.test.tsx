import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RegimeBadge } from "@/components/charts/RegimeBadge";

describe("<RegimeBadge>", () => {
  it("renders trend regime label in Russian", () => {
    render(<RegimeBadge regime="trend" />);
    expect(screen.getByText("Тренд")).toBeInTheDocument();
  });

  it("renders flat regime label", () => {
    render(<RegimeBadge regime="flat" />);
    expect(screen.getByText("Флэт")).toBeInTheDocument();
  });

  it("renders high_vol regime with caution color class", () => {
    const { container } = render(<RegimeBadge regime="high_vol" />);
    expect(screen.getByText("Волатильность")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-hermes-wine");
  });

  it("includes the symbol in small mode", () => {
    render(<RegimeBadge regime="trend" symbol="EURUSD" small />);
    expect(screen.getByText("EURUSD")).toBeInTheDocument();
  });
});
