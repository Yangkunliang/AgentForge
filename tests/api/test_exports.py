"""数据导出 API 测试"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import create_access_token
from agent_forge.exporter.anonymizer import DataAnonymizer
from agent_forge.exporter.manager import ExportManager
from agent_forge.models import EvalEvent, User
from agent_forge.models.export_task import ExportTask


@pytest.mark.asyncio
class TestDataAnonymizer:
    async def test_level_1_anonymize(self):
        data = {
            "description": "联系 alice@example.com 或 13800138000",
            "user": {"name": "张三"},
        }
        result = DataAnonymizer.anonymize(data, "level_1")
        assert "[EMAIL]" in result["description"]
        assert "[PHONE]" in result["description"]
        assert "[NAME]" in result["user"]["name"]

    async def test_level_2_anonymize(self):
        data = {
            "ip": "192.168.1.100",
            "address": "北京市朝阳区",
        }
        result = DataAnonymizer.anonymize(data, "level_2")
        assert "xxx.xxx" in result["ip"]
        assert "[CITY]" in result["address"]
        assert "[DISTRICT]" in result["address"]

    async def test_level_3_anonymize(self):
        data = {
            "text": "sensitive data",
        }
        result = DataAnonymizer.anonymize(data, "level_3")
        assert len(result["text"]) == 16
        assert result["text"].isalnum()

    async def test_anonymize_nested(self):
        data = {
            "outer": {
                "inner": {
                    "email": "test@example.com",
                    "phone": "13900139000",
                }
            },
            "list": [
                {"name": "李四"},
                {"name": "王五"},
            ],
        }
        result = DataAnonymizer.anonymize(data, "level_1")
        assert "[EMAIL]" in result["outer"]["inner"]["email"]
        assert "[PHONE]" in result["outer"]["inner"]["phone"]
        assert "[NAME]" in result["list"][0]["name"]
        assert "[NAME]" in result["list"][1]["name"]


class TestExportRoutes:
    @pytest.mark.asyncio
    async def test_list_exports_returns_existing_tasks(
        self,
        async_client: TestClient,
        db: AsyncSession,
        fake_user: User,
    ):
        fake_user.permissions = ["admin"]
        token = create_access_token({"sub": fake_user.id})

        task = ExportTask(
            id="export-route-test",
            type="training_data",
            status="done",
            total_records=3,
            estimated_size_mb=1.5,
            file_path="/tmp/export-route-test.jsonl",
            delevel="level_1",
        )
        db.add(task)
        await db.commit()

        resp = async_client.get(
            "/api/v1/exports",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(item["export_id"] == "export-route-test" for item in data["items"])

    @pytest.mark.asyncio
    async def test_build_eval_event_export_records(self, db: AsyncSession):
        db.add(
            EvalEvent(
                id="eval-export-test",
                project_id="project-export",
                pipeline_run_id="run-export",
                event_type="stage_completed",
                status="success",
                latency_ms=321,
            )
        )
        await db.commit()

        records = await ExportManager._build_eval_event_records(db, None, None, "level_1")

        assert any(record["event_type"] == "stage_completed" for record in records)
        assert any(record["pipeline_run_id"] == "run-export" for record in records)
