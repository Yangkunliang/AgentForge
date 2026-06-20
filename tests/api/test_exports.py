"""数据导出 API 测试"""

from __future__ import annotations

import pytest

from agent_forge.exporter.anonymizer import DataAnonymizer


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