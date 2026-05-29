import { AnimatePresence, motion } from "framer-motion";
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
          {/* Page transitions: route-keyed fade + slide. AnimatePresence handles
              the leave animation while the new route is mounting. */}
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.25, ease: [0.2, 0.65, 0.3, 1] }}
            >
              {/* Per-route ErrorBoundary: a crash inside Dashboard / Trades /
                  any single page renders the boundary's recovery screen,
                  but the sidebar, the title bar, and the rest of the SPA
                  keep working. Navigation to another page resets the
                  boundary because key=location.pathname forces a remount. */}
              <ErrorBoundary key={location.pathname}>
                <Outlet />
              </ErrorBoundary>
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      <div className="md:hidden">
        <BottomNav />
      </div>
    </div>
  );
}
