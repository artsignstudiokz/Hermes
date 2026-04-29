import { Minus, Search, Square, X } from "lucide-react";

import { BrandMark } from "@/components/ui/BrandMark";
import { win } from "@/lib/webview";
import { cn } from "@/lib/utils";

/**
 * Frameless window title bar.
 *  - Drag region (left + center)
 *  - ⌘K hint button (opens command palette via keyboard event dispatch)
 *  - Native window controls (min/max/close) via PyWebView bridge
 */
export function TitleBar() {
  const openPalette = () => {
    // Forward to the global ⌘K handler in CommandPalette.
    window.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", metaKey: true, ctrlKey: true, bubbles: true }),
    );
  };

  return (
    <div
      className={cn(
        "titlebar-drag relative flex h-10 select-none items-center justify-between px-3",
        "border-b border-hermes-gold/25 bg-hermes-marble/85 backdrop-blur-md",
      )}
    >
      <div className="flex items-center gap-2 pl-1">
        <BrandMark size="sm" showText />
      </div>

      {/* Center: ⌘K shortcut tile */}
      <button
        onClick={openPalette}
        className="titlebar-nodrag absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 inline-flex items-center gap-2 rounded-md border border-hermes-gold/25 bg-hermes-alabaster/70 px-2.5 py-1 text-[11px] text-hermes-navy/55 transition hover:border-hermes-gold/45 hover:text-hermes-navy"
        aria-label="Открыть командную палитру"
        title="⌘K — командная палитра"
      >
        <Search size={11} />
        <span>Куда идём?</span>
        <kbd className="rounded border border-hermes-gold/30 bg-hermes-marble px-1 font-mono text-[9px]">
          ⌘K
        </kbd>
      </button>

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
