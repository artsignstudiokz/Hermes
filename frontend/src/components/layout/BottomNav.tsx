import { NavLink } from "react-router-dom";
import { LayoutDashboard, ListOrdered, Cog, Bell, Info } from "lucide-react";

import { cn } from "@/lib/utils";

const ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Олимп" },
  { to: "/trades", icon: ListOrdered, label: "Сделки" },
  { to: "/strategy", icon: Cog, label: "Настройки" },
  { to: "/notifications", icon: Bell, label: "Уведом." },
  { to: "/about", icon: Info, label: "О боте" },
];

export function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-hermes-gold/30 bg-hermes-marble/95 backdrop-blur-md">
      <ul className="grid grid-cols-5">
        {ITEMS.map((it) => (
          <li key={it.to}>
            <NavLink
              to={it.to}
              end={it.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center gap-1 py-2.5 text-[11px]",
                  isActive ? "text-hermes-gold-deep" : "text-muted-foreground",
                )
              }
            >
              <it.icon size={20} />
              <span>{it.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
