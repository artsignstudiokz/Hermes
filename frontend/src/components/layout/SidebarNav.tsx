import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Bell,
  Building2,
  ChevronLeft,
  Cog,
  Info,
  LayoutDashboard,
  ListOrdered,
  ScrollText,
  Smartphone,
  Sparkles,
  TestTube,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
  hint?: string;
}

interface NavSection {
  id: string;
  title: string;
  items: NavItem[];
}

const SECTIONS: NavSection[] = [
  {
    id: "trading",
    title: "Олимп",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Главная", hint: "Equity · позиции · режим" },
      { to: "/trades", icon: ListOrdered, label: "Сделки", hint: "История + статистика" },
      { to: "/strategy", icon: Cog, label: "Стратегия", hint: "Пресеты + параметры" },
      { to: "/brokers", icon: Building2, label: "Брокеры", hint: "MT5 · Binance · Bybit" },
    ],
  },
  {
    id: "analysis",
    title: "Анализ",
    items: [
      { to: "/backtest", icon: TestTube, label: "Бэктест", hint: "Прогон по истории" },
      { to: "/optimize", icon: Sparkles, label: "Оптимизация", hint: "Optuna trials" },
    ],
  },
  {
    id: "system",
    title: "Система",
    items: [
      { to: "/mobile", icon: Smartphone, label: "На телефон", hint: "QR + туннель" },
      { to: "/notifications", icon: Bell, label: "Уведомления", hint: "Web Push · Telegram" },
      { to: "/logs", icon: ScrollText, label: "Журнал", hint: "Логи системы" },
      { to: "/settings", icon: SlidersHorizontal, label: "Настройки", hint: "Тема · обновления" },
      { to: "/about", icon: Info, label: "О боте", hint: "BAI Core" },
    ],
  },
];

const STORAGE_KEY = "hermes.sidebar.collapsed";

export function SidebarNav() {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed));
  }, [collapsed]);

  return (
    <motion.nav
      animate={{ width: collapsed ? 76 : 264 }}
      transition={{ type: "spring", stiffness: 220, damping: 26 }}
      className={cn(
        "relative flex flex-col border-r border-hermes-gold/20 bg-hermes-alabaster/55 backdrop-blur-md",
        "py-5",
      )}
    >
      {/* Brand */}
      <div className={cn("flex items-center gap-2.5 px-4 pb-5", collapsed && "justify-center px-2")}>
        <img
          src="/hermes-favicon.png"
          alt=""
          width={collapsed ? 28 : 34}
          height={collapsed ? 28 : 34}
          className="select-none transition-all"
          draggable={false}
        />
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className="leading-tight"
          >
            <div className="font-serif text-base font-semibold tracking-wide text-hermes-navy">HERMES</div>
            <div className="text-[8px] uppercase tracking-[0.28em] text-hermes-gold-deep">
              Trading · BAI Core
            </div>
          </motion.div>
        )}
      </div>

      {/* Sections */}
      <div className="flex-1 overflow-y-auto px-2 space-y-5">
        {SECTIONS.map((section) => (
          <div key={section.id}>
            {!collapsed && (
              <div className="mb-1.5 px-3 text-[9px] font-semibold uppercase tracking-[0.32em] text-muted-foreground/70">
                {section.title}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map((it) => (
                <NavItemLink key={it.to} item={it} collapsed={collapsed} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-3 border-t border-hermes-gold/15 px-3 pt-3">
        <button
          onClick={() => setCollapsed((v) => !v)}
          className={cn(
            "flex w-full items-center gap-2 rounded-lg px-2 py-2 text-xs text-muted-foreground transition",
            "hover:bg-hermes-parchment/60 hover:text-foreground",
            collapsed && "justify-center",
          )}
          aria-label={collapsed ? "Развернуть" : "Свернуть"}
          title={collapsed ? "Развернуть" : "Свернуть"}
        >
          <motion.span
            animate={{ rotate: collapsed ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="inline-flex"
          >
            <ChevronLeft size={14} />
          </motion.span>
          {!collapsed && <span>Свернуть</span>}
        </button>

        {!collapsed && (
          <a
            href="https://baicore.kz"
            target="_blank"
            rel="noreferrer"
            className="mt-2 block rounded-lg px-2 py-1.5 text-center text-[10px] uppercase tracking-[0.24em] text-muted-foreground transition hover:text-hermes-gold-deep"
          >
            Разработано BAI Core
          </a>
        )}
      </div>
    </motion.nav>
  );
}

function NavItemLink({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      className={({ isActive }) =>
        cn(
          "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
          "hover:bg-hermes-parchment/60 hover:text-foreground",
          isActive
            ? "bg-marble-grain font-semibold text-hermes-navy shadow-card"
            : "text-muted-foreground",
          collapsed && "justify-center px-2",
        )
      }
      title={collapsed ? item.label : undefined}
    >
      {({ isActive }) => (
        <>
          {/* Active rail accent */}
          {isActive && (
            <motion.span
              layoutId="sidebar-active-rail"
              className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r-full bg-hermes-gold-deep"
              transition={{ type: "spring", stiffness: 320, damping: 28 }}
            />
          )}
          <item.icon
            size={17}
            className={cn(
              "shrink-0 transition",
              isActive ? "text-hermes-gold-deep" : "text-muted-foreground group-hover:text-hermes-gold",
            )}
          />
          {!collapsed && (
            <>
              <span className="flex-1 truncate">{item.label}</span>
              {isActive && (
                <span className="h-1.5 w-1.5 rounded-full bg-hermes-gold animate-gold-pulse" />
              )}
            </>
          )}
        </>
      )}
    </NavLink>
  );
}
