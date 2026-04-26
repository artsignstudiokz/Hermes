import { Minus, Square, X } from "lucide-react";

import { BrandMark } from "@/components/ui/BrandMark";
import { win } from "@/lib/webview";
import { cn } from "@/lib/utils";

/** Frameless window title bar. Drag region + min/max/close + brand. */
export function TitleBar() {
  return (
    <div
      className={cn(
        "titlebar-drag relative flex h-10 select-none items-center justify-between px-3",
        "border-b border-hermes-gold/25 bg-hermes-marble/80 backdrop-blur-md",
      )}
    >
      <div className="flex items-center gap-2 pl-1">
        <BrandMark size="sm" showText />
      </div>

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[11px] uppercase tracking-[0.28em] text-hermes-navy/55">
        Бог торговли. Ваш бот.
      </div>

      <div className="titlebar-nodrag flex items-center gap-1">
        <button
          aria-label="Свернуть"
          onClick={() => win.minimize()}
          className="grid h-7 w-9 place-items-center rounded-md text-hermes-navy/55 transition hover:bg-hermes-parchment hover:text-hermes-navy"
        >
          <Minus size={14} />
        </button>
        <button
          aria-label="Развернуть"
          onClick={() => win.maximize()}
          className="grid h-7 w-9 place-items-center rounded-md text-hermes-navy/55 transition hover:bg-hermes-parchment hover:text-hermes-navy"
        >
          <Square size={12} />
        </button>
        <button
          aria-label="Закрыть"
          onClick={() => win.close()}
          className="grid h-7 w-9 place-items-center rounded-md text-hermes-navy/55 transition hover:bg-destructive hover:text-destructive-foreground"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
