import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ListOrdered,
  Cog,
  TestTube,
  Sparkles,
  Smartphone,
  Bell,
  ScrollText,
  Info,
  Building2,
  SlidersHorizontal,
} from "lucide-react";

import { cn } from "@/lib/utils";

const ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Олимп", hint: "Главная" },
  { to: "/trades", icon: ListOrdered, label: "Сделки", hint: "История" },
  { to: "/strategy", icon: Cog, label: "Стратегия", hint: "Настройки" },
  { to: "/brokers", icon: Building2, label: "Брокеры", hint: "Подключения" },
  { to: "/backtest", icon: TestTube, label: "Бэктест", hint: "Прошлое" },
  { to: "/optimize", icon: Sparkles, label: "Оптимизация", hint: "Auto-tune" },
  { to: "/mobile", icon: Smartphone, label: "На телефон", hint: "Удалённый доступ" },
  { to: "/notifications", icon: Bell, label: "Уведомления", hint: "Web Push / TG" },
  { to: "/logs", icon: ScrollText, label: "Журнал", hint: "Логи" },
  { to: "/settings", icon: SlidersHorizontal, label: "Настройки", hint: "Тема, обновления" },
  { to: "/about", icon: Info, label: "О боте", hint: "BAI Core" },
];

export function SidebarNav() {
  return (
    <nav className="flex w-64 flex-col gap-1 border-r border-hermes-gold/20 bg-hermes-alabaster/60 px-3 py-6">
      <div className="flex items-center gap-2 px-3 pb-4">
        <img
          src="/hermes-favicon.png"
          alt=""
          width={32}
          height={32}
          className="select-none"
          draggable={false}
        />
        <div className="leading-tight">
          <div className="font-serif text-base font-semibold tracking-wide text-hermes-navy">
            HERMES
          </div>
          <div className="text-[9px] uppercase tracking-[0.28em] text-hermes-gold-deep">
            Trading Bot · BAI Core
          </div>
        </div>
      </div>
      {ITEMS.map((it) => (
        <NavLink
          key={it.to}
          to={it.to}
          end={it.to === "/"}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
              isActive
                ? "bg-marble-grain text-foreground shadow-card font-semibold"
                : "text-muted-foreground hover:bg-hermes-parchment/60 hover:text-foreground",
            )
          }
        >
          {({ isActive }) => (
            <>
              <it.icon
                size={18}
                className={cn(
                  "shrink-0 transition",
                  isActive ? "text-hermes-gold-deep" : "text-muted-foreground group-hover:text-hermes-gold",
                )}
              />
              <span className="flex-1">{it.label}</span>
              {isActive && (
                <span className="h-1.5 w-1.5 rounded-full bg-hermes-gold animate-gold-pulse" />
              )}
            </>
          )}
        </NavLink>
      ))}
      <div className="mt-auto px-3 pt-6 text-center">
        <div className="text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
          Разработано
        </div>
        <a
          href="https://baicore.kz"
          target="_blank"
          rel="noreferrer"
          className="mt-1 inline-block font-serif text-base text-hermes-gold-deep hover:text-hermes-bronze transition"
        >
          BAI Core
        </a>
      </div>
    </nav>
  );
}
