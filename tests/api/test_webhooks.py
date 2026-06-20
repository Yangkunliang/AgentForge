"""Webhook API 测试"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.webhooks import WebhookManager
from agent_forge.webhooks.manager import SUPPORTED_EVENTS


@pytest.mark.asyncio
class TestWebhookManager:
    async def test_register_webhook(self, db: AsyncSession):
        webhook, secret_key = await WebhookManager.register_webhook(
            db,
            user_id="user-001",
            url="https://example.com/webhook",
            events=["task.completed", "task.failed"],
        )
        assert webhook.url == "https://example.com/webhook"
        assert "task.completed" in webhook.events
        assert len(secret_key) == 64

    async def test_get_webhook(self, db: AsyncSession):
        webhook, _ = await WebhookManager.register_webhook(
            db,
            user_id="user-002",
            url="https://test.com/webhook",
            events=["task.completed"],
        )

        retrieved = await WebhookManager.get_webhook(db, webhook.id)
        assert retrieved is not None
        assert retrieved.url == "https://test.com/webhook"

    async def test_list_webhooks(self, db: AsyncSession):
        await WebhookManager.register_webhook(
            db,
            user_id="user-003",
            url="https://test1.com/webhook",
            events=["task.completed"],
        )
        await WebhookManager.register_webhook(
            db,
            user_id="user-003",
            url="https://test2.com/webhook",
            events=["task.failed"],
        )

        webhooks = await WebhookManager.list_webhooks(db, "user-003")
        assert len(webhooks) == 2

    async def test_delete_webhook(self, db: AsyncSession):
        webhook, _ = await WebhookManager.register_webhook(
            db,
            user_id="user-004",
            url="https://delete.com/webhook",
            events=["task.completed"],
        )

        success = await WebhookManager.delete_webhook(db, webhook.id)
        assert success is True

        retrieved = await WebhookManager.get_webhook(db, webhook.id)
        assert retrieved is None

    async def test_update_webhook(self, db: AsyncSession):
        webhook, _ = await WebhookManager.register_webhook(
            db,
            user_id="user-005",
            url="https://old.com/webhook",
            events=["task.completed"],
        )

        updated = await WebhookManager.update_webhook(
            db,
            webhook.id,
            url="https://new.com/webhook",
            events=["task.failed"],
            is_active=False,
        )
        assert updated is not None
        assert updated.url == "https://new.com/webhook"
        assert "task.failed" in updated.events
        assert updated.is_active is False


@pytest.mark.asyncio
class TestWebhookSignature:
    async def test_generate_signature(self):
        signature = WebhookManager._generate_signature("secret", "payload")
        assert len(signature) == 64

    async def test_verify_signature(self):
        secret = "my-secret"
        payload = '{"event": "task.completed"}'
        signature = WebhookManager._generate_signature(secret, payload)

        assert WebhookManager.verify_signature(secret, payload, signature) is True
        assert WebhookManager.verify_signature(secret, payload, "wrong") is False
        assert WebhookManager.verify_signature("wrong-secret", payload, signature) is False


@pytest.mark.asyncio
class TestSupportedEvents:
    async def test_supported_events(self):
        assert "task.completed" in SUPPORTED_EVENTS
        assert "task.failed" in SUPPORTED_EVENTS
        assert "task.created" in SUPPORTED_EVENTS
        assert "task.cancelled" in SUPPORTED_EVENTS