/**
 * Action-driven tutorial steps. Each step waits for the operator to
 * DO something - navigate to a page, click a target button, or reach
 * a backend state. The tutorial advances automatically when the
 * detector fires. Manual fallback button exists for impatient users.
 *
 * Anchors and click-targets are stable contract: components mark
 * themselves with `data-tour="<id>"` so steps reference them by id
 * rather than fragile CSS selectors.
 */

export type TutorialAction =
  | { type: "manual" }                          // operator clicks "Далее"
  | { type: "navigate"; path: string }          // wait for the URL to match
  | { type: "click"; tour: string }             // wait for data-tour click
  | { type: "state"; key: string };             // poll a state detector

export interface TutorialStep {
  id: string;
  title: string;
  body: string;
  hint?: string;
  anchor: string | null;        // [data-tour="..."] to highlight, null = floating
  action: TutorialAction;
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: "welcome",
    title: "Привет от Гермеса",
    body:
      "Сейчас я покажу как со мной работать. Каждый шаг просит сделать одно конкретное " +
      "действие. Я сам перейду к следующему когда вы его выполните.",
    hint: "Нажмите «Поехали» когда будете готовы.",
    anchor: null,
    action: { type: "manual" },
  },
  {
    id: "open-strategy",
    title: "Шаг 1: откройте Стратегию",
    body:
      "В левом меню найдите раздел «Стратегия». Здесь настраивается какие инструменты я " +
      "использую и на каких парах работаю.",
    hint: "Кликните на «Стратегия» в боковой панели.",
    anchor: "[href='/strategy']",
    action: { type: "navigate", path: "/strategy" },
  },
  {
    id: "see-strategies",
    title: "Шаг 2: посмотрите на стратегии",
    body:
      "Внизу страницы есть блок «Стратегии анализа». По умолчанию активны Trend Following и " +
      "Momentum - они показали положительное ожидание на backtest. Mean Reversion и Breakout " +
      "опционально - включайте если хотите экспериментировать.",
    hint: "Прокрутите вниз чтобы увидеть чекбоксы.",
    anchor: null,
    action: { type: "manual" },
  },
  {
    id: "back-dashboard",
    title: "Шаг 3: вернитесь на Дашборд",
    body:
      "Главный экран - центр управления. Тут баланс, открытые позиции, equity-кривая, " +
      "кнопки запуска двух режимов.",
    hint: "Кликните на «Главная» в боковой панели.",
    anchor: "[href='/']",
    action: { type: "navigate", path: "/" },
  },
  {
    id: "two-modes",
    title: "Шаг 4: два режима торговли",
    body:
      "Видите две кнопки «Проверенный» и «Автономный»? Это и есть два пути:\n\n" +
      "🛡 ПРОВЕРЕННЫЙ - одна стратегия, 3-5 пар, строгие условия, 1-3 сделки в день.\n\n" +
      "🧠 АВТОНОМНЫЙ - все выбранные стратегии, любая пара, выбирает где сигнал сильнее.\n\n" +
      "За раз работает только один режим.",
    hint: "Просто посмотрите. Нажмите «Понятно» когда осознаете.",
    anchor: "[data-tour='start-buttons']",
    action: { type: "manual" },
  },
  {
    id: "test-trade",
    title: "Шаг 5: тестовая сделка",
    body:
      "Прямо сейчас можно проверить что бот реально открывает ордера. Кнопка «Разовый " +
      "анализ» сделает быстрый прогон по всем парам и покажет какая выглядит лучше всех. " +
      "Сделку при этом не открывает - только показывает отчёт.",
    hint: "Нажмите «Разовый анализ» (или «Понятно» если не хотите сейчас).",
    anchor: "[data-tour='analyze-btn']",
    action: { type: "manual" },
  },
  {
    id: "open-trades",
    title: "Шаг 6: история сделок",
    body:
      "Перейдите в раздел «Сделки». Каждая сделка раскрывается кликом и показывает " +
      "почему бот её открыл - какие индикаторы согласились, какая стратегия сработала, " +
      "уверенность. Свои наблюдения можно сохранить в заметках справа.",
    hint: "Кликните на «Сделки» в боковой панели.",
    anchor: "[href='/trades']",
    action: { type: "navigate", path: "/trades" },
  },
  {
    id: "settings",
    title: "Шаг 7: безопасность и поддержка",
    body:
      "В Настройках вы найдёте: тему, проверку обновлений, перезапуск этого тура, и " +
      "кнопку скачать архив логов если потребуется помощь.",
    hint: "Кликните на «Настройки» в боковой панели.",
    anchor: "[href='/settings']",
    action: { type: "navigate", path: "/settings" },
  },
  {
    id: "done",
    title: "Готов к работе",
    body:
      "Это всё что нужно знать на старте. Я наблюдаю рынок и пишу обоснование каждому " +
      "решению. Risk Engine защищает от слива, SL/TP уходят к брокеру при открытии. " +
      "Telegram-нотификации настраиваются в разделе «Уведомления». Удачи в торговле.",
    hint: "Нажмите «Завершить».",
    anchor: null,
    action: { type: "manual" },
  },
];
