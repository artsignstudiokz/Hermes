# Hermes Landing — Astro 5

Лендинг для **Hermes** (торговый бот от **BAI Core**).
Стек: **Astro 5 + TypeScript + Tailwind 3** → деплой на **Vercel**.

## Локально

```bash
cd landing
npm install
npm run dev          # http://localhost:4321
```

Production build:
```bash
npm run build        # → dist/
npm run preview      # сервер dist/
```

## Структура

```
landing/
├── public/                    # static assets, копируются как есть
│   ├── hermes-emblem.svg      # каundлей с золотым градиентом
│   ├── meander.svg            # греческий ключ
│   ├── baicore-logo.svg
│   ├── robots.txt
│   └── releases/              # установщики (НЕ коммитятся, добавляются CI)
│       ├── Hermes-Setup-1.0.0.exe
│       └── Hermes-1.0.0.pkg
├── src/
│   ├── layouts/
│   │   └── Layout.astro       # base HTML, OG, шрифты, мета
│   ├── components/
│   │   ├── BrandMark.astro
│   │   ├── Header.astro
│   │   ├── Hero.astro         # анимированная монета + smart download
│   │   ├── Features.astro     # 6 карточек
│   │   ├── HowItWorks.astro   # α / β / γ
│   │   ├── Screenshots.astro  # мокап интерфейса
│   │   ├── Specs.astro        # брокеры / системы
│   │   ├── Download.astro     # карточки скачивания
│   │   ├── FAQ.astro
│   │   └── Footer.astro
│   ├── lib/
│   │   └── downloads.ts       # OS → URL
│   ├── styles/
│   │   └── globals.css        # Tailwind + кастомные классы
│   └── pages/
│       └── index.astro        # склейка + клиентский <script>
├── astro.config.mjs           # @astrojs/vercel + sitemap + tailwind
├── tailwind.config.mjs        # бренд-палитра Hermes (мрамор + золото)
├── tsconfig.json              # extends astro/tsconfigs/strict + path aliases
├── vercel.json                # security headers + cache control
├── package.json
└── .gitignore
```

## Кастомизация

- **Цвета**: `tailwind.config.mjs` (`marble`, `gold`, `olive`, `wine`, `aegean`, `ink`).
- **Шрифты**: Cormorant Garamond + Inter + JetBrains Mono — подключаются в `Layout.astro`.
- **URL установщиков**: `src/lib/downloads.ts` — заменить пути после первого CI-релиза.
- **Контент**: данные секций — массивы вверху каждого `.astro` компонента.

## Деплой на Vercel

### Первый раз
```bash
cd landing
npx vercel link        # привязать к проекту (создать новый: hermes-landing)
npx vercel --prod
```

Vercel сам определит фреймворк (`framework: "astro"` в `vercel.json`),
подтянет `npm install` и `npm run build`, выложит `dist/` через CDN.

### Привязка домена
1. В Vercel → Project → Settings → Domains добавить `hermes.baicore.kz`.
2. В hoster.kz DNS-менеджере: создать **CNAME** запись `hermes` → `cname.vercel-dns.com`.
3. Подождать 5–30 мин, SSL выдастся автоматически.

### Git workflow
```bash
# в корне monorepo (trading_bot/), один раз:
git init
git add landing/
git commit -m "Hermes landing v1.0"
gh repo create hermes-landing --public --source=landing --push
```

После этого Vercel автоматически деплоит каждый push в main.

## Как добавить установщики

Когда `scripts/build_release.ps1` сгенерирует `dist/Hermes.exe` и `Hermes-Setup-1.0.0.exe`:

1. Залить файлы в GitHub Release страницу `hermes-landing` (или другого репо).
2. В `landing/src/lib/downloads.ts` заменить URL:
   ```ts
   windows: { url: "https://github.com/.../releases/download/v1.0.0/Hermes-Setup-1.0.0.exe", ... }
   ```
3. Закоммитить — Vercel переразвернёт лендинг автоматически.

Альтернатива: загружать в `public/releases/` напрямую (сейчас .exe / .pkg в `.gitignore` — снять
исключение если хотите хранить в репо, но не рекомендуется для файлов > 25 МБ).

## Performance

Цель: Lighthouse 100 / 100 / 100 / 100.
- Astro генерирует zero-JS HTML по умолчанию.
- Только один `<script>` блок в `index.astro` — для интерактива (OS detection, scroll reveal).
- Изображения: SVG inline. Шрифты с `display=swap` + preconnect.
- Все CSS-анимации с поддержкой `prefers-reduced-motion`.
