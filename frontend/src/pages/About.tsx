import { ExternalLink, Mail } from "lucide-react";

import { brand } from "@/theme/tokens";
import { win } from "@/lib/webview";

export function About() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="flex flex-col items-center gap-4 text-center">
        <img
          src="/hermes-logo.png"
          alt="Hermes Trading Bot"
          className="h-32 w-auto select-none drop-shadow-md"
          draggable={false}
        />
        <p className="font-serif text-2xl italic text-hermes-navy/65">
          {brand.godName} · {brand.subtitle}
        </p>
      </div>

      <div className="marble-card p-8">
        <h2 className="display text-2xl font-semibold">О боге торговли</h2>
        <p className="mt-3 font-serif text-base leading-relaxed text-muted-foreground">
          В греческой мифологии Гермес — посланник богов и покровитель торговцев, путников и удачи.
          Hermes — это алгоритмическая воплощение его роли: круглосуточный спутник трейдера,
          анализирующий рынок и совершающий сделки от вашего имени.
        </p>
      </div>

      <div className="marble-card p-8">
        <div className="flex items-center justify-between">
          <h2 className="display text-2xl font-semibold">Разработчик</h2>
          <span className="text-xs uppercase tracking-wider text-muted-foreground">v1.0.0</span>
        </div>
        <div className="mt-4 flex flex-col gap-3 text-sm">
          <div className="flex items-center gap-3">
            <span className="font-serif text-2xl text-hermes-gold-deep">BAI Core</span>
            <span className="text-muted-foreground">— компания, создавшая Hermes</span>
          </div>
          <button
            onClick={() => win.openExternal(brand.developerUrl)}
            className="inline-flex items-center gap-2 self-start text-hermes-aegean hover:underline"
          >
            <ExternalLink size={14} /> {brand.developerUrl.replace("https://", "")}
          </button>
          <button
            onClick={() => win.openExternal(`mailto:${brand.developerEmail}`)}
            className="inline-flex items-center gap-2 self-start text-hermes-aegean hover:underline"
          >
            <Mail size={14} /> {brand.developerEmail}
          </button>
        </div>
      </div>

      <div className="text-center text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
        © {new Date().getFullYear()} BAI Core · Сделано в Казахстане
      </div>
    </div>
  );
}
