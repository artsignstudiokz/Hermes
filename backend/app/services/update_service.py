"""Auto-update — checks baicore.kz for newer Hermes releases.

Endpoint contract (`GET https://baicore.kz/api/hermes/latest`):

    {
      "version": "1.0.1",
      "released_at": "2026-05-15T10:00:00Z",
      "windows": { "url": "https://...exe", "sha256": "...", "size": 81234567 },
      "macos":   { "url": "https://...pkg", "sha256": "...", "size": 84567890 },
      "notes": "What's new (markdown)"
    }

The frontend renders `notes` as markdown in the Settings page; the desktop
launcher can later download + verify hash + spawn the installer.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

import httpx

from app import __version__

logger = logging.getLogger(__name__)

UPDATE_URL = "https://baicore.kz/api/hermes/latest"
USER_AGENT = f"Hermes/{__version__} (+https://baicore.kz)"


@dataclass(frozen=True)
class PlatformAsset:
    url: str
    sha256: str
    size: int


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    has_update: bool
    released_at: str | None
    notes: str | None
    asset: PlatformAsset | None         # for the current OS only


def _semver_tuple(v: str) -> tuple[int, ...]:
    """Parse "1.0.1" or "1.0.1-rc.2" → (1, 0, 1). Pre-release is treated < release."""
    base = v.split("-", 1)[0]
    parts = base.split(".")
    nums: list[int] = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    return tuple(nums)


def _platform_key() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


async def check_for_update(*, timeout: float = 6.0) -> UpdateInfo:
    """Fetch the manifest and compare against current version."""
    try:
        async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
            r = await client.get(UPDATE_URL)
            r.raise_for_status()
            data = r.json()
    except Exception as e:  # noqa: BLE001
        logger.info("Update check failed: %s", e)
        return UpdateInfo(
            current_version=__version__,
            latest_version=__version__,
            has_update=False,
            released_at=None,
            notes=None,
            asset=None,
        )

    latest = str(data.get("version", __version__))
    has_update = _semver_tuple(latest) > _semver_tuple(__version__)

    plat = data.get(_platform_key()) or {}
    asset: PlatformAsset | None = None
    if plat.get("url"):
        asset = PlatformAsset(
            url=str(plat["url"]),
            sha256=str(plat.get("sha256", "")),
            size=int(plat.get("size", 0)),
        )

    return UpdateInfo(
        current_version=__version__,
        latest_version=latest,
        has_update=has_update,
        released_at=data.get("released_at"),
        notes=data.get("notes"),
        asset=asset,
    )
