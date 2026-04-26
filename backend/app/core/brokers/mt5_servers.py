"""Scan the local Windows machine for installed MetaTrader 5 terminals
and the broker servers configured in each.

Approach:
  1. Walk every `terminal64.exe` / `terminal.exe` under common install roots
     and `%APPDATA%\MetaQuotes\Terminal\<HASH>` (cached terminals from
     portable installs and re-installs).
  2. For each terminal, read `<terminal>\config\accounts.ini` — every
     section is one previously-used account/server combo.
  3. Parse `servers.dat` if accounts.ini is missing: it's a binary blob,
     but the server names are stored as null-terminated wide strings —
     we extract printable ASCII tokens that look like server identifiers.

Result is broker/server list for the BrokerForm autocomplete; missing
fields just degrade gracefully — the user can always type a server name
manually.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MT5Server:
    name: str                 # e.g. "MetaQuotes-Demo"
    broker: str | None = None # e.g. "MetaQuotes Software Corp."
    terminal_path: str | None = None


@dataclass(frozen=True)
class MT5Installation:
    path: str                 # full path to the terminal executable
    data_dir: str             # path to the per-terminal config dir
    is_portable: bool = False


# Heuristic root candidates we probe. Order matters — prefer Program Files.
_TERMINAL_BINARIES = ("terminal64.exe", "terminal.exe")


def _candidate_roots() -> list[Path]:
    if sys.platform != "win32":
        return []
    roots: list[Path] = []
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        v = os.environ.get(env_var)
        if v:
            roots.append(Path(v))
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / "MetaQuotes" / "Terminal")
    # User's home — covers sideloaded installations.
    roots.append(Path.home())
    # Drives root (depth-limited scan kicks in at the next layer).
    return roots


def _looks_like_terminal_dir(p: Path) -> bool:
    return p.is_dir() and any((p / b).exists() for b in _TERMINAL_BINARIES)


def list_installations(max_results: int = 40) -> list[MT5Installation]:
    """Best-effort scan. Caps the search to avoid walking the entire C:\\."""
    if sys.platform != "win32":
        return []

    found: dict[str, MT5Installation] = {}

    def _add(terminal_dir: Path, *, is_portable: bool = False) -> None:
        for binary in _TERMINAL_BINARIES:
            exe = terminal_dir / binary
            if exe.exists():
                # Each terminal has a per-install data dir. For non-portable
                # installs this lives under %APPDATA%\MetaQuotes\Terminal\<HASH>.
                # For portable installs it's the install dir itself.
                data_dir = terminal_dir if is_portable else _resolve_data_dir(terminal_dir)
                key = str(exe.resolve())
                if key not in found:
                    found[key] = MT5Installation(
                        path=key, data_dir=str(data_dir), is_portable=is_portable,
                    )

    for root in _candidate_roots():
        if not root.exists():
            continue
        try:
            # Depth-2 scan under each root. Avoids walking the whole drive.
            for first_level in root.iterdir():
                if not first_level.is_dir():
                    continue
                if _looks_like_terminal_dir(first_level):
                    _add(first_level)
                    if len(found) >= max_results:
                        return list(found.values())
                    continue
                try:
                    for second_level in first_level.iterdir():
                        if _looks_like_terminal_dir(second_level):
                            _add(second_level)
                            if len(found) >= max_results:
                                return list(found.values())
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            continue

    # Plus every cached profile under %APPDATA%\MetaQuotes\Terminal\<HASH>.
    appdata = os.environ.get("APPDATA")
    if appdata:
        terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
        if terminal_root.exists():
            for hash_dir in terminal_root.iterdir():
                if hash_dir.is_dir() and (hash_dir / "config").exists():
                    key = str(hash_dir.resolve())
                    if key not in found:
                        found[key] = MT5Installation(
                            path=key + r"\terminal64.exe",
                            data_dir=str(hash_dir),
                            is_portable=False,
                        )

    return list(found.values())


def _resolve_data_dir(terminal_dir: Path) -> Path:
    """For non-portable MT5 installs, config lives in %APPDATA%\\MetaQuotes\\Terminal\\<HASH>."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return terminal_dir
    terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
    if not terminal_root.exists():
        return terminal_dir
    # Pick the most-recently-modified profile dir as our best guess.
    candidates = [d for d in terminal_root.iterdir() if d.is_dir() and (d / "config").exists()]
    if not candidates:
        return terminal_dir
    candidates.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return candidates[0]


def list_servers() -> list[MT5Server]:
    """Return a deduplicated list of broker servers known to local terminals."""
    if sys.platform != "win32":
        return _fallback_servers()

    seen: dict[str, MT5Server] = {}

    for inst in list_installations():
        data_dir = Path(inst.data_dir)
        config_dir = data_dir / "config"
        if not config_dir.exists():
            continue

        # 1. accounts.ini — easy structured source.
        accounts_ini = config_dir / "accounts.ini"
        if accounts_ini.exists():
            for srv in _parse_accounts_ini(accounts_ini):
                if srv.name not in seen:
                    seen[srv.name] = MT5Server(
                        name=srv.name, broker=srv.broker, terminal_path=inst.path,
                    )

        # 2. servers.dat — binary, fish out plausible server identifiers.
        servers_dat = config_dir / "servers.dat"
        if servers_dat.exists():
            for name in _scrape_servers_dat(servers_dat):
                if name not in seen:
                    seen[name] = MT5Server(name=name, broker=None, terminal_path=inst.path)

    if not seen:
        return _fallback_servers()
    return sorted(seen.values(), key=lambda s: s.name.lower())


def _parse_accounts_ini(path: Path) -> list[MT5Server]:
    parser = ConfigParser(strict=False, interpolation=None)
    try:
        parser.read(path, encoding="utf-16")
    except Exception:
        try:
            parser.read(path, encoding="utf-8")
        except Exception:
            logger.debug("Failed to parse accounts.ini at %s", path)
            return []
    out: list[MT5Server] = []
    for section in parser.sections():
        try:
            server = parser.get(section, "Server", fallback=None)
            company = parser.get(section, "Company", fallback=None)
        except Exception:
            continue
        if server:
            out.append(MT5Server(name=server.strip(), broker=company))
    return out


def _scrape_servers_dat(path: Path) -> list[str]:
    """Heuristic — server names look like 'BrokerName-Real|Demo|MT5...'."""
    try:
        blob = path.read_bytes()
    except Exception:
        return []
    # Wide-char (UTF-16-LE) strings: every other byte is null.
    try:
        text_w = blob.decode("utf-16-le", errors="ignore")
    except Exception:
        text_w = ""
    text_a = blob.decode("ascii", errors="ignore")

    pattern = re.compile(r"\b([A-Za-z][\w]{2,30}-[\w]{2,30}(?:-?[\w]{0,30})?)\b")
    candidates: set[str] = set()
    for m in pattern.findall(text_w + "\n" + text_a):
        # Filter junk: must contain a dash and look like Broker-Server.
        if 6 <= len(m) <= 64 and "-" in m and not m.startswith("-"):
            candidates.add(m)
    return sorted(candidates)


def _fallback_servers() -> list[MT5Server]:
    """When MT5 isn't installed or autodetect failed."""
    return [
        MT5Server(name="MetaQuotes-Demo", broker="MetaQuotes (Demo)"),
        MT5Server(name="Exness-MT5Trial", broker="Exness"),
        MT5Server(name="Exness-MT5Real", broker="Exness"),
        MT5Server(name="RoboForex-MetaTrader5", broker="RoboForex"),
        MT5Server(name="RoboForex-Demo", broker="RoboForex"),
        MT5Server(name="XMGlobal-MT5", broker="XM"),
        MT5Server(name="FBS-Demo", broker="FBS"),
        MT5Server(name="FBS-Real", broker="FBS"),
        MT5Server(name="Alpari-MT5-Demo", broker="Alpari"),
        MT5Server(name="Alpari-MT5", broker="Alpari"),
        MT5Server(name="InstaForex-1MT5.com", broker="InstaForex"),
    ]
