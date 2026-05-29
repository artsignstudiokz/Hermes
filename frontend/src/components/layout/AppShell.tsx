import { Outlet, useLocation } from "react-router-dom";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { SidebarNav } from "./SidebarNav";
import { BottomNav } from "./BottomNav";

export function AppShell() {
  const location = useLocation();

  return (
    <div className="flex flex-1 overflow-hidden">
      <aside className="hidden md:flex">
        <SidebarNav />
      </aside>

      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <div className="mx-auto max-w-7xl px-6 py-8">
          {/* v1.0.36: removed AnimatePresence + motion.div route wrapper.
              On WebView2 with --disable-gpu the route-enter animation
              was running concurrently with Dashboard's own entry
              animation AND every per-widget animation in BalanceCard /
              BotStatusBadge / RegimeBadge. All of those CPU-composited
              at once was a real renderer-killer on the affected
              machine. Per-route ErrorBoundary stays - it isolates a
              page crash to that page. */}
          <ErrorBoundary key={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </div>
      </main>

      <div className="md:hidden">
        <BottomNav />
      </div>
    </div>
  );
}
