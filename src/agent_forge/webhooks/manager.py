"""Webhook 管理器 - 注册、触发、验证 Webhook"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models.webhook import Webhook

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = [
    "task.completed",
    "task.failed",
    "task.created",
    "task.cancelled",
]


class WebhookManager:
    _webhook_cache: dict[str, list[Webhook]] = {}

    @classmethod
    async def register_webhook(
        cls,
        db: AsyncSession,
        user_id: str,
        url: str,
        events: list[str],
        description: str | None = None,
    ) -> tuple[Webhook, str]:
        webhook_id = f"wh-{secrets.token_hex(8)}"
        secret_key = secrets.token_hex(32)

        webhook = Webhook(
            id=webhook_id,
            user_id=user_id,
            url=url,
            events=events,
            secret_key=secret_key,
            is_active=True,
            description=description,
        )
        db.add(webhook)
        await db.commit()

        cls._invalidate_cache(user_id)

        return webhook, secret_key

    @classmethod
    async def get_webhook(cls, db: AsyncSession, webhook_id: str) -> Webhook | None:
        result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
        return result.scalar_one_or_none()

    @classmethod
    async def list_webhooks(cls, db: AsyncSession, user_id: str) -> list[Webhook]:
        result = await db.execute(select(Webhook).where(Webhook.user_id == user_id))
        return list(result.scalars().all())

    @classmethod
    async def delete_webhook(cls, db: AsyncSession, webhook_id: str) -> bool:
        webhook = await cls.get_webhook(db, webhook_id)
        if webhook:
            user_id = webhook.user_id
            await db.delete(webhook)
            await db.commit()
            cls._invalidate_cache(user_id)
            return True
        return False

    @classmethod
    async def update_webhook(
        cls,
        db: AsyncSession,
        webhook_id: str,
        url: str | None = None,
        events: list[str] | None = None,
        is_active: bool | None = None,
    ) -> Webhook | None:
        webhook = await cls.get_webhook(db, webhook_id)
        if not webhook:
            return None

        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if is_active is not None:
            webhook.is_active = is_active

        await db.commit()
        cls._invalidate_cache(webhook.user_id)
        return webhook

    @classmethod
    async def trigger_webhook(
        cls, db: AsyncSession, event: str, data: dict[str, Any]
    ) -> int:
        result = await db.execute(
            select(Webhook).where(
                Webhook.is_active == True,  # noqa: E712
            )
        )
        webhooks = list(result.scalars().all())

        matching_webhooks = [wh for wh in webhooks if event in wh.events]

        if not matching_webhooks:
            return 0

        tasks = []
        for webhook in matching_webhooks:
            task = asyncio.create_task(
                cls._send_webhook(webhook, event, data)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        return success_count

    @classmethod
    async def _send_webhook(
        cls, webhook: Webhook, event: str, data: dict[str, Any]
    ) -> bool:
        try:
            payload = {
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }

            body = json.dumps(payload, ensure_ascii=False)
            signature = cls._generate_signature(webhook.secret_key, body)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Signature": f"sha256={signature}",
                    },
                )

            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook {webhook.id} triggered successfully for {event}")
                return True
            else:
                logger.warning(
                    f"Webhook {webhook.id} returned {response.status_code}: {response.text[:200]}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to trigger webhook {webhook.id}: {e}")
            return False

    @classmethod
    def _generate_signature(cls, secret: str, payload: str) -> str:
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def verify_signature(cls, secret: str, payload: str, signature: str) -> bool:
        expected = cls._generate_signature(secret, payload)
        return hmac.compare_digest(expected, signature)

    @classmethod
    def _invalidate_cache(cls, user_id: str) -> None:
        cls._webhook_cache.pop(user_id, None)
