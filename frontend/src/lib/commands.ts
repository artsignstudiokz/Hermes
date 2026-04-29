/**
 * Command palette registry. Commands are static — they're just navigation
 * and a few imperative actions. Fuzzy search is a simple substring match
 * weighted by where the term hits (label > section > description).
 */

import type { LucideIcon } from "lucide-react";

import {
  Bell,
  Building2,
  Cog,
  Info,
  LayoutDashboard,
  ListOrdered,
  ScrollText,
  Smartphone,
  SlidersHorizontal,
  Sparkles,
  TestTube,
} from "lucide-react";

export interface Command {
  id: string;
  section: string;
  label: string;
  description?: string;
  icon?: LucideIcon;
  to?: string;                 // navigate route
  action?: () => void;         // imperative
  keywords?: string[];         // extra search terms
  shortcut?: string;           // display only
}

export const COMMANDS: Command[] = [
  // Navigation
  { id: "nav-home",     section: "Навигация", label: "Главная (Олимп)",  icon: LayoutDashboard,    to: "/",             keywords: ["dashboard", "olimp"] },
  { id: "nav-trades",   section: "Навигация", label: "Сделки",           icon: ListOrdered,        to: "/trades",       keywords: ["history", "trades"] },
  { id: "nav-strategy", section: "Навигация", label: "Стратегия",        icon: Cog,                to: "/strategy",     keywords: ["preset", "params"] },
  { id: "nav-brokers",  section: "Навигация", label: "Брокеры",          icon: Building2,          to: "/brokers",      keywords: ["mt5", "binance", "bybit"] },
  { id: "nav-backtest", section: "Анализ",    label: "Бэктест",          icon: TestTube,           to: "/backtest",     keywords: ["history test"] },
  { id: "nav-optimize", section: "Анализ",    label: "Оптимизация",      icon: Sparkles,           to: "/optimize",     keywords: ["optuna"] },
  { id: "nav-mobile",   section: "Система",   label: "На телефон",       icon: Smartphone,         to: "/mobile",       keywords: ["qr", "ngrok"] },
  { id: "nav-notif",    section: "Система",   label: "Уведомления",      icon: Bell,               to: "/notifications", keywords: ["push", "telegram"] },
  { id: "nav-logs",     section: "Система",   label: "Журнал",           icon: ScrollText,         to: "/logs",         keywords: ["logs"] },
  { id: "nav-settings", section: "Система",   label: "Настройки",        icon: SlidersHorizontal,  to: "/settings",     keywords: ["theme", "update"] },
  { id: "nav-about",    section: "Система",   label: "О боте",           icon: Info,               to: "/about",        keywords: ["bai core", "version"] },
];

export function rankCommands(query: string, all: Command[] = COMMANDS): Command[] {
  const q = query.trim().toLowerCase();
  if (!q) return all;
  const tokens = q.split(/\s+/);

  type Scored = { cmd: Command; score: number };
  const scored: Scored[] = [];

  for (const cmd of all) {
    const haystack = [
      cmd.label.toLowerCase(),
      cmd.section.toLowerCase(),
      cmd.description?.toLowerCase() ?? "",
      ...(cmd.keywords ?? []).map((k) => k.toLowerCase()),
    ].join("  ");

    let score = 0;
    let allTokensMatched = true;

    for (const tok of tokens) {
      const labelHit = cmd.label.toLowerCase().includes(tok);
      const sectionHit = cmd.section.toLowerCase().includes(tok);
      const otherHit = haystack.includes(tok);
      if (labelHit) score += 10;
      else if (sectionHit) score += 4;
      else if (otherHit) score += 2;
      else { allTokensMatched = false; break; }
    }

    if (allTokensMatched && score > 0) scored.push({ cmd, score });
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.map((s) => s.cmd);
}
