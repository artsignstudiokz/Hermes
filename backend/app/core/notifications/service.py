"""NotificationService — fan-out trade events to Web Push + Telegram + WS.

WS broadcast already happens inside the trading worker; this service handles
the off-screen channels (push & Telegram) and is invoked from the same place.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notifications.telegram import TelegramClient
from app.core.notifications.templates import render
from app.core.notifications.webpush import ensure_vapid_keys, send_webpush
from app.core.security.vault import CredentialVault
from app.db.models import NotificationSub
from app.db.session import get_sessionmaker
from app.settings import Settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, vault: CredentialVault, settings: Settings) -> None:
        self._vault = vault
        self._settings = settings
        self._vapid_path = settings.data_dir / "vapid.json"

    @property
    def vapid_public_key(self) -> str:
        return ensure_vapid_keys(self._vapid_path)["public_b64url"]

    @property
    def vapid_private_pem(self) -> str:
        return ensure_vapid_keys(self._vapid_path)["private_pem"]

    async def dispatch(self, event: dict) -> None:
        """Render once → push to all enabled subs in parallel-ish (best effort)."""
        rendered = render(event, locale=self._settings.locale)
        sm = get_sessionmaker()
        async with sm() as session:
            await self._dispatch_webpush(session, rendered, event)
            await self._dispatch_telegram(session, rendered)

    async def _dispatch_webpush(
        self, session: AsyncSession, msg: dict[str, str], event: dict,
    ) -> None:
        rows = (await session.execute(
            select(NotificationSub).where(
                NotificationSub.type == "webpush", NotificationSub.enabled.is_(True),
            ),
        )).scalars().all()
        if not rows:
            return
        payload = {
            "title": msg["title"],
            "body": msg["body"],
            "icon": "/hermes-emblem.svg",
            "badge": "/hermes-emblem.svg",
            "data": {"event": event},
        }
        for r in rows:
            send_webpush(
                endpoint=r.endpoint,
                p256dh=r.p256dh or "",
                auth=r.auth or "",
                payload=payload,
                vapid_private_pem=self.vapid_private_pem,
            )

    async def _dispatch_telegram(self, session: AsyncSession, msg: dict[str, str]) -> None:
        rows = (await session.execute(
            select(NotificationSub).where(
                NotificationSub.type == "telegram", NotificationSub.enabled.is_(True),
            ),
        )).scalars().all()
        for r in rows:
            # endpoint = bot token; chat_id is in p256dh slot (reused for compactness).
            token = r.endpoint
            chat_id = r.p256dh or ""
            if not token or not chat_id:
                continue
            await TelegramClient(token, chat_id).send(msg["body_long"])

    async def test(self) -> dict[str, int]:
        """Send a hello to all enabled subs. Returns counts."""
        await self.dispatch({"type": "test", "message": "Hermes на связи."})
        sm = get_sessionmaker()
        async with sm() as session:
            wp = (await session.execute(
                select(NotificationSub).where(
                    NotificationSub.type == "webpush", NotificationSub.enabled.is_(True),
                ),
            )).scalars().all()
            tg = (await session.execute(
                select(NotificationSub).where(
                    NotificationSub.type == "telegram", NotificationSub.enabled.is_(True),
                ),
            )).scalars().all()
        return {"webpush": len(wp), "telegram": len(tg)}


_service: NotificationService | None = None


def init_notification_service(vault: CredentialVault, settings: Settings) -> NotificationService:
    global _service
    _service = NotificationService(vault, settings)
    return _service


def get_notification_service() -> NotificationService:
    if _service is None:
        raise RuntimeError("NotificationService not initialised")
    return _service
