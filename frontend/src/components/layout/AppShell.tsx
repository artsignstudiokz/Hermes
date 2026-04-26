import { Outlet } from "react-router-dom";

import { SidebarNav } from "./SidebarNav";
import { BottomNav } from "./BottomNav";

export function AppShell() {
  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex">
        <SidebarNav />
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom nav */}
      <div className="md:hidden">
        <BottomNav />
      </div>
    </div>
  );
}
