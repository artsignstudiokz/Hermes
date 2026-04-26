"""Native splash screen shown before the webview window appears.

Uses the standard library only (Tkinter) to avoid pulling Qt/etc. into
PyInstaller. The frontend renders a richer splash inside the webview
on top of this — once the webview is ready, the Tk splash is destroyed.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk


class SplashWindow:
    def __init__(self, logo_path: Path, brand: str = "Hermes — Trading Bot") -> None:
        self._logo_path = logo_path
        self._brand = brand
        self._tk_root: "tk.Tk | None" = None
        self._thread: threading.Thread | None = None
        self._closed = threading.Event()

    def show(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        self._tk_root = root
        root.overrideredirect(True)

        # Hermes brand: marble background + navy text + gold accent.
        BG = "#FBF7EC"
        FG_NAVY = "#1B2940"
        FG_GOLD = "#A8884F"
        FG_MUTED = "#7e7163"
        root.configure(bg=BG)

        # Center on screen.
        w, h = 480, 300
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.attributes("-topmost", True)

        try:
            if self._logo_path.exists() and self._logo_path.suffix.lower() in {".png", ".gif"}:
                logo = tk.PhotoImage(file=str(self._logo_path))
                tk.Label(root, image=logo, bg=BG).pack(pady=(56, 14))
                root._logo_ref = logo  # type: ignore[attr-defined]
        except Exception:
            pass

        tk.Label(
            root,
            text=self._brand,
            fg=FG_NAVY,
            bg=BG,
            font=("Segoe UI", 16, "bold"),
        ).pack()
        tk.Label(
            root,
            text="Бог торговли. Ваш бот.",
            fg=FG_GOLD,
            bg=BG,
            font=("Segoe UI", 10),
        ).pack(pady=(4, 12))
        tk.Label(
            root,
            text="Запуск...",
            fg=FG_MUTED,
            bg=BG,
            font=("Segoe UI", 10),
        ).pack()
        tk.Label(
            root,
            text="© BAI Core · baicore.kz",
            fg=FG_MUTED,
            bg=BG,
            font=("Segoe UI", 9),
        ).pack(side="bottom", pady=12)

        # Keep the loop alive until close() is called.
        def _poll() -> None:
            if self._closed.is_set():
                root.destroy()
                return
            root.after(80, _poll)

        root.after(80, _poll)
        try:
            root.mainloop()
        except Exception:
            pass

    def close(self) -> None:
        self._closed.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._tk_root = None
