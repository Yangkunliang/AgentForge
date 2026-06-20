"""Webhook API 路由"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import get_current_active_user
from agent_forge.database import get_async_session
from agent_forge.models.user import User
from agent_forge.webhooks import SUPPORTED_EVENTS, WebhookManager

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class RegisterWebhookRequest(BaseModel):
    url: str
    events: list[str]
    description: str | None = None


class WebhookResponse(BaseModel):
    webhook_id: str
    url: str
    events: list[str]
    secret_key: str
    description: str | None


class WebhookListItem(BaseModel):
    webhook_id: str
    url: str
    events: list[str]
    is_active: bool
    description: str | None


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_webhook(
    request: RegisterWebhookRequest,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
):
    for event in request.events:
        if event not in SUPPORTED_EVENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported event: {event}. Supported: {SUPPORTED_EVENTS}",
            )

    webhook, secret_key = await WebhookManager.register_webhook(
        db, user.id, request.url, request.events, request.description
    )

    return WebhookResponse(
        webhook_id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        secret_key=secret_key,
        description=webhook.description,
    )


@router.get("")
async def list_webhooks(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
):
    webhooks = await WebhookManager.list_webhooks(db, user.id)
    return {
        "total": len(webhooks),
        "items": [
            WebhookListItem(
                webhook_id=wh.id,
                url=wh.url,
                events=wh.events,
                is_active=wh.is_active,
                description=wh.description,
            )
            for wh in webhooks
        ],
    }


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
):
    webhook = await WebhookManager.get_webhook(db, webhook_id)
    if not webhook or webhook.user_id != user.id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookListItem(
        webhook_id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
):
    webhook = await WebhookManager.get_webhook(db, webhook_id)
    if not webhook or webhook.user_id != user.id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await WebhookManager.delete_webhook(db, webhook_id)


@router.get("/events")
async def list_supported_events():
    return {"events": SUPPORTED_EVENTS}