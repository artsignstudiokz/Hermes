# Hermes — Trading Bot

> Бог торговли в облике алгоритма. Профессиональная автоматическая торговля.
> Разработано **BAI Core** ([baicore.kz](https://baicore.kz)).

Hermes — это десктоп-приложение для автоматической торговли на Forex и
криптовалютном рынке. Устанавливается одним инсталлятором (как браузер),
запускается в собственном окне, поддерживает MT5 и крипто-биржи (Binance / Bybit / OKX).

## Возможности

- **Один инсталлятор** — `Hermes-Setup-1.0.0.exe` для Windows, `.pkg` для macOS. Без Python, pip, командной строки.
- **Десктоп-приложение** — собственное окно с иконкой Hermes в таскбаре. Не вкладка браузера.
- **Светлый дизайн в стиле античной мифологии** — мрамор, золото, оливковая ветвь.
- **Безопасность** — ключи бирж шифруются Argon2id + Fernet под мастер-паролем.
- **Адаптивная торговля** — раз в неделю авто-калибровка параметров с walk-forward защитой от overfitting.
- **Mobile-доступ** — кнопка «Открыть с телефона» поднимает ngrok-туннель + QR + PIN.
- **Веб-уведомления** — Web Push (PWA) и Telegram дублируются.

## Структура проекта

```
trading_bot/
├── desktop/           PyWebView wrapper — точка входа .exe (single-instance, splash, native window)
├── backend/           FastAPI приложение (REST + WebSocket + SQLite)
│   └── app/
│       ├── api/       Routes, WebSocket, Pydantic-схемы
│       ├── core/      Доменное ядро: brokers, strategy, adaptive, security, notifications
│       ├── db/        SQLAlchemy 2 + Alembic
│       ├── services/  Use-case слой
│       └── workers/   asyncio-воркеры (trading loop, calibration)
├── frontend/          React + Vite + TypeScript + Tailwind + shadcn/ui
│   └── src/
│       ├── pages/     Dashboard, Onboarding, Unlock, Trades, ...
│       ├── components/ TitleBar, Splash, AppShell, charts, widgets
│       ├── theme/     Hermes design tokens (мрамор + золото)
│       └── lib/       api, ws, format, webview bridge
├── legacy/            Старый код (стратегия, индикаторы, бэктестер) — переиспользуется
├── packaging/
│   ├── pyinstaller/   PyInstaller spec → один Hermes.exe
│   └── windows/       Inno Setup installer + ассеты
├── scripts/           dev_backend.ps1, dev_frontend.ps1, dev_desktop.ps1, build_release.ps1
└── trading_bot/       Старая Streamlit-сборка (оставлена как референс, удаляется в Фазе 6)
```

## Разработка

### Требования
- Python 3.11+
- Node.js 20+
- (Windows) Inno Setup 6 — для сборки инсталлятора

### Запуск dev-стека

```powershell
# Установка зависимостей (один раз)
pip install -e backend[dev,desktop]
cd frontend
npm install
cd ..

# Запуск всего стека (3 терминала открываются автоматически)
.\scripts\dev_desktop.ps1
```

Откроется десктоп-окно Hermes, подключённое к Vite dev-серверу с HMR
и FastAPI на `127.0.0.1:8765`.

### Сборка релиза

```powershell
.\scripts\build_release.ps1
```

Результат:
- `dist\Hermes.exe` — standalone-исполняемый файл
- `dist\installer\Hermes-Setup-1.0.0.exe` — установщик с UX как у браузеров

## Изображения Гермеса

В папке `frontend/public/hermes/` лежит README с рекомендациями, какие public-domain
фото статуй Гермеса добавить (Hermes Praxiteles, Hermes Belvedere). Файлы автоматически
подключаются на страницах Onboarding и Settings.

## Безопасность

- Все API-ключи шифруются Argon2id + Fernet с использованием мастер-пароля.
- Backend слушает только `127.0.0.1`.
- Удалённый доступ открывается отдельно через ngrok-туннель + 6-значный PIN (rotate каждые 24 ч).
- Подробнее: `docs/SECURITY.md` (создаётся в Фазе 6).

## Roadmap

См. `C:\Users\User\.claude\plans\generic-tinkering-wall.md`. Шесть фаз, ~9–10 недель.

## Лицензия

© BAI Core. Все права защищены. По вопросам коммерческой лицензии — info@baicore.kz.
