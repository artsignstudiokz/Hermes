from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.notification import (
    NotificationSubOut,
    TelegramSubscribeRequest,
    TestResult,
    VapidPublicKey,
    WebPushSubscribeRequest,
)
from app.core.notifications.service import NotificationService, get_notification_service
from app.core.notifications.telegram import TelegramClient
from app.db.models import NotificationSub
from app.deps import get_db_session

router = APIRouter()


def _short(text: str, n: int = 40) -> str:
    return text[:n] + ("…" if len(text) > n else "")


@router.get("/vapid-public", response_model=VapidPublicKey)
async def vapid_public(
    svc: NotificationService = Depends(get_notification_service),
) -> VapidPublicKey:
    return VapidPublicKey(key=svc.vapid_public_key)


@router.get("/subs", response_model=list[NotificationSubOut])
async def list_subs(session: AsyncSession = Depends(get_db_session)) -> list[NotificationSubOut]:
    rows = (await session.execute(select(NotificationSub).order_by(NotificationSub.id))).scalars().all()
    return [
        NotificationSubOut(
            id=r.id, type=r.type, endpoint_short=_short(r.endpoint), enabled=r.enabled,
        )
        for r in rows
    ]


@router.post("/webpush/subscribe", response_model=NotificationSubOut, status_code=status.HTTP_201_CREATED)
async def webpush_subscribe(
    req: WebPushSubscribeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> NotificationSubOut:
    # Replace any existing sub for the same endpoint.
    existing = (await session.execute(
        select(NotificationSub).where(NotificationSub.endpoint == req.endpoint),
    )).scalar_one_or_none()
    if existing:
        existing.p256dh = req.p256dh
        existing.auth = req.auth
        existing.enabled = True
        row = existing
    else:
        row = NotificationSub(
            type="webpush", endpoint=req.endpoint, p256dh=req.p256dh, auth=req.auth, enabled=True,
        )
        session.add(row)
    await session.commit()
    await session.refresh(row)
    return NotificationSubOut(id=row.id, type=row.type, endpoint_short=_short(row.endpoint), enabled=row.enabled)


@router.post("/telegram/subscribe", response_model=NotificationSubOut, status_code=status.HTTP_201_CREATED)
async def telegram_subscribe(
    req: TelegramSubscribeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> NotificationSubOut:
    # Validate by sending a test message.
    ok = await TelegramClient(req.bot_token, req.chat_id).test()
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Telegram credentials are invalid")
    existing = (await session.execute(
        select(NotificationSub).where(
            NotificationSub.type == "telegram", NotificationSub.endpoint == req.bot_token,
        ),
    )).scalar_one_or_none()
    if existing:
        existing.p256dh = req.chat_id
        existing.enabled = True
        row = existing
    else:
        row = NotificationSub(
            type="telegram", endpoint=req.bot_token, p256dh=req.chat_id, enabled=True,
        )
        session.add(row)
    await session.commit()
    await session.refresh(row)
    return NotificationSubOut(
        id=row.id, type=row.type,
        endpoint_short=f"chat={req.chat_id}", enabled=row.enabled,
    )


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sub(sub_id: int, session: AsyncSession = Depends(get_db_session)) -> None:
    row = await session.get(NotificationSub, sub_id)
    if row:
        await session.delete(row)
        await session.commit()


@router.patch("/{sub_id}/toggle", response_model=NotificationSubOut)
async def toggle_sub(
    sub_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> NotificationSubOut:
    row = await session.get(NotificationSub, sub_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    row.enabled = not row.enabled
    await session.commit()
    return NotificationSubOut(id=row.id, type=row.type, endpoint_short=_short(row.endpoint), enabled=row.enabled)


@router.post("/test", response_model=TestResult)
async def test(svc: NotificationService = Depends(get_notification_service)) -> TestResult:
    return TestResult(**(await svc.test()))
