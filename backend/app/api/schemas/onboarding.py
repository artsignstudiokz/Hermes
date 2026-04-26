from __future__ import annotations

from pydantic import BaseModel


class MT5ServerOut(BaseModel):
    name: str
    broker: str | None = None
    terminal_path: str | None = None


class MT5InstallationOut(BaseModel):
    path: str
    data_dir: str
    is_portable: bool


class OnboardingStatus(BaseModel):
    first_run: bool
    vault_initialised: bool
    has_broker: bool
    has_strategy: bool
    is_running: bool
    next_step: str   # "master_password" | "broker" | "strategy" | "start" | "done"
