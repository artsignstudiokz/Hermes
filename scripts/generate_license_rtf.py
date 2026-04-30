"""Generate packaging/windows/assets/license.rtf as pure-ASCII RTF.

RTF has a bytes-encoding ambiguity: \\ansicpg1251 means "interpret raw bytes
as CP1251", but the source file is usually saved UTF-8 by editors. The
clean portable solution is to encode every non-ASCII character as
`\\uNNNN?` (Unicode escape with ASCII fallback). This produces a valid
RTF readable by Inno Setup, Word, WordPad, macOS TextEdit, anything.

Run:  python scripts/generate_license_rtf.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "packaging" / "windows" / "assets" / "license.rtf"

# ── Polished license text (Russian) ───────────────────────────────────────
LICENSE_TITLE = "Лицензионное соглашение Hermes"
SECTIONS = [
    ("",
     "Hermes — десктоп-приложение для автоматической алгоритмической торговли "
     "на Forex и криптовалютных рынках. Разработчик: BAI Core (baicore.kz)."),

    ("",
     "Перед установкой пожалуйста ознакомьтесь с условиями ниже. "
     "Установка и использование Hermes означает ваше согласие с этими условиями."),

    ("1. Финансовые риски",
     "Вы понимаете и принимаете все риски, связанные с автоматической торговлей "
     "на финансовых рынках, включая возможность полной потери вложенных средств. "
     "BAI Core не несёт ответственности за финансовые результаты, возникшие "
     "в результате использования Hermes."),

    ("2. Хранение секретов",
     "Все пароли и API-ключи бирж хранятся локально на вашем компьютере "
     "и шифруются мастер-паролем (Argon2id + Fernet AES-128). Мастер-пароль "
     "не передаётся на серверы BAI Core ни при каких обстоятельствах. "
     "В случае утери мастер-пароля восстановление доступа к зашифрованным "
     "данным невозможно."),

    ("3. Допустимое использование",
     "Hermes можно использовать в личных целях или в законных коммерческих "
     "проектах. Запрещено использовать программу для нарушения правил "
     "вашего брокера, биржи или применимого законодательства, "
     "а также для манипулирования рынком."),

    ("4. Гарантии",
     "Программа предоставляется «как есть», без каких-либо явных или "
     "подразумеваемых гарантий. BAI Core оставляет за собой право вносить "
     "изменения в работу Hermes, выпускать обновления и прекращать поддержку "
     "отдельных версий."),

    ("5. Контакты",
     "По вопросам сотрудничества: info@baicore.kz\n"
     "Техническая поддержка: support@baicore.kz\n"
     "Сайт компании: https://baicore.kz"),
]

FOOTER = (
    "© BAI Core. Все права защищены. "
    "Hermes возносится над рынками."
)


def _escape(s: str) -> str:
    """Convert Unicode string to RTF-escaped ASCII."""
    out: list[str] = []
    for ch in s:
        n = ord(ch)
        if ch in ("\\", "{", "}"):
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\par\n")
        elif n > 127:
            out.append(f"\\u{n}?")
        else:
            out.append(ch)
    return "".join(out)


def build_rtf() -> str:
    parts: list[str] = []
    # RTF prelude — declares font + a sensible default code page (1251).
    # The Unicode escapes are the actual source of truth though; \\ansicpg
    # only matters for any literal non-ASCII bytes (we have none).
    parts.append(r"{\rtf1\ansi\ansicpg1251\deff0\nouicompat\deflang1049")
    parts.append(r"{\fonttbl{\f0\fnil\fcharset204 Segoe UI;}}")
    parts.append(r"{\colortbl ;\red27\green41\blue64;\red168\green136\blue79;\red100\green100\blue100;}")
    parts.append(r"\viewkind4\uc1")
    parts.append(r"\pard\sa180\sl288\slmult1\fs22")
    parts.append("")

    # Title — large, bold, navy color (\\cf1).
    parts.append(r"{\fs32\b\cf1 " + _escape(LICENSE_TITLE) + r"\b0\par}")
    parts.append(r"\pard\sa180\sl276\slmult1\fs20\par")

    for heading, body in SECTIONS:
        if heading:
            parts.append(r"{\fs24\b\cf2 " + _escape(heading) + r"\b0\par}")
        parts.append(r"\pard\sa120\sl276\slmult1\fs20 " + _escape(body) + r"\par")
        parts.append(r"\par")

    # Footer — italic, muted gray.
    parts.append(r"\pard\qc\sa120\sl276\slmult1\fs18\cf3\i " + _escape(FOOTER) + r"\i0\par")

    parts.append("}")
    return "\n".join(parts)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_rtf(), encoding="ascii")
    size = OUT.stat().st_size
    print(f"OK  -> {OUT.relative_to(ROOT)}  ({size} bytes, ASCII)")


if __name__ == "__main__":
    main()
