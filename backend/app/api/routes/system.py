"""System endpoints: health, version, logs tail."""

from __future__ import annotations

import logging
import platform
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import __brand__, __product__, __version__
from app.deps import get_app_settings
from app.services.update_service import check_for_update
from app.settings import Settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ClientError(BaseModel):
    message: str
    stack: str = ""
    component_stack: str = ""


class HealthResponse(BaseModel):
    ok: bool
    product: str
    brand: str
    version: str
    platform: str


class LogsResponse(BaseModel):
    lines: list[str]


class UpdateAsset(BaseModel):
    url: str
    sha256: str
    size: int


class UpdateCheckResponse(BaseModel):
    current_version: str
    latest_version: str
    has_update: bool
    released_at: str | None
    notes: str | None
    asset: UpdateAsset | None


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        product=__product__,
        brand=__brand__,
        version=__version__,
        platform=f"{platform.system()} {platform.release()}",
    )


@router.get("/version")
async def version() -> dict[str, str]:
    return {"version": __version__, "product": __product__, "brand": __brand__}


@router.get("/logs", response_model=LogsResponse)
async def tail_logs(
    tail: int = Query(default=200, ge=1, le=5000),
    settings: Settings = Depends(get_app_settings),
) -> LogsResponse:
    log_file: Path = settings.log_file
    if not log_file.exists():
        return LogsResponse(lines=[])
    with log_file.open("r", encoding="utf-8", errors="replace") as f:
        lines = list(deque(f, maxlen=tail))
    return LogsResponse(lines=[ln.rstrip("\n") for ln in lines])


class UiPrefs(BaseModel):
    tutorial_done: bool = False
    tutorial_version: str = ""


def _prefs_path(settings: "Settings") -> Path:
    return settings.data_dir / "ui-prefs.json"


@router.get("/ui-prefs", response_model=UiPrefs)
async def get_ui_prefs(settings: Settings = Depends(get_app_settings)) -> UiPrefs:
    """Read UI preferences from disk.

    Why backend instead of localStorage: PyWebView opens the SPA on an
    ephemeral 127.0.0.1 port that changes on every restart. localStorage
    scopes to host+port, so the "tutorial completed" flag was lost on
    every relaunch, and the tour kept replaying. Storing it in
    %APPDATA%\\BAI Core\\Hermes\\ui-prefs.json survives restarts.
    """
    import json
    p = _prefs_path(settings)
    if not p.exists():
        return UiPrefs()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return UiPrefs(**data)
    except Exception:
        return UiPrefs()


@router.post("/ui-prefs", response_model=UiPrefs)
async def set_ui_prefs(
    body: UiPrefs,
    settings: Settings = Depends(get_app_settings),
) -> UiPrefs:
    import json
    p = _prefs_path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.model_dump_json(indent=2), encoding="utf-8")
    return body


@router.get("/logs/bundle")
async def logs_bundle(
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    """Pack the last 14 days of hermes.log plus a small system report
    into a single ZIP the operator can attach to a support request.

    Deliberately scrubs nothing - the operator can edit the archive
    before sending. Vault file and credentials.enc are EXCLUDED by
    path, never touched.
    """
    import io
    import zipfile
    import platform as _plat

    log_file: Path = settings.log_file
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if log_file.exists():
            zf.write(log_file, arcname="hermes.log")
        # Companion file with environment + version info.
        report = (
            f"Hermes {__version__} ({__product__} by {__brand__})\n"
            f"OS: {_plat.system()} {_plat.release()} ({_plat.machine()})\n"
            f"Python: {_plat.python_version()}\n"
            f"Data dir: {settings.data_dir}\n"
        )
        zf.writestr("system-report.txt", report)
    buf.seek(0)
    filename = f"hermes-logs-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}.zip"
    return StreamingResponse(
        iter([buf.read()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/log-client-error", status_code=204)
async def log_client_error(err: ClientError) -> None:
    # SPA reports JS errors / unhandled rejections here so they survive
    # in hermes.log. --windowed builds have no devtools by default.
    logger.error(
        "[client] %s\nStack: %s\nComponent: %s",
        err.message, err.stack, err.component_stack,
    )


class ClientTrace(BaseModel):
    stage: str


@router.post("/trace", status_code=204)
async def client_trace(t: ClientTrace) -> None:
    # SPA boot-progress beacons - if WebView2 dies mid-render, the
    # log shows the last stage that fired. See main.tsx::trace().
    logger.info("[client-trace] %s", t.stage)


@router.post("/check-update", response_model=UpdateCheckResponse)
async def check_update() -> UpdateCheckResponse:
    info = await check_for_update()
    return UpdateCheckResponse(
        current_version=info.current_version,
        latest_version=info.latest_version,
        has_update=info.has_update,
        released_at=info.released_at,
        notes=info.notes,
        asset=UpdateAsset(**info.asset.__dict__) if info.asset else None,
    )
