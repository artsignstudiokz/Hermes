"""Find an available ephemeral port on 127.0.0.1."""

from __future__ import annotations

import socket


def find_free_port() -> int:
    """Bind to port 0 and let the OS pick a free port, then release it.

    There is a small race between release and re-bind by uvicorn, but it's
    acceptable for a single-user desktop app on loopback only.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
