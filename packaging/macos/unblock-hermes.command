#!/usr/bin/env bash
# One-click helper: removes the macOS "quarantine" attribute from Hermes.app
# so the user doesn't have to dig through System Settings.
#
# Distribution: include this file alongside Hermes-1.0.0.pkg on the download
# page. Mac users who hit the "unidentified developer" warning double-click
# this script and Gatekeeper allows the app on next launch.

set -euo pipefail

APP_CANDIDATES=(
  "/Applications/Hermes.app"
  "$HOME/Applications/Hermes.app"
  "$HOME/Downloads/Hermes.app"
)

APP=""
for candidate in "${APP_CANDIDATES[@]}"; do
  if [ -d "$candidate" ]; then
    APP="$candidate"
    break
  fi
done

if [ -z "$APP" ]; then
  osascript -e 'display alert "Hermes не найден" message "Не нашли Hermes.app в /Applications/, ~/Applications/ или ~/Downloads/. Перетащите этот файл в папку с Hermes и запустите ещё раз." as critical'
  exit 1
fi

echo "Снимаем карантин с $APP …"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

# Re-apply ad-hoc signature in case extracting from a .pkg stripped it.
codesign --deep --force --sign - "$APP" 2>/dev/null || true

osascript -e "display dialog \"Готово! Запустите Hermes из Launchpad.\nЕсли macOS снова попросит подтверждение — нажмите 'Открыть'.\" buttons {\"OK\"} default button \"OK\" with icon note with title \"Hermes by BAI Core\""
