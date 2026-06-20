"""数据脱敏器 - 支持多级别脱敏策略"""

from __future__ import annotations

import hashlib
import re
from typing import Any


class DataAnonymizer:
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
    IP_PATTERN = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
    NAME_PATTERN = re.compile(r"[\u4e00-\u9fa5]{2,4}")

    @classmethod
    def anonymize(cls, data: dict[str, Any], delevel: str = "level_1") -> dict[str, Any]:
        if delevel == "level_1":
            return cls._level_1(data)
        elif delevel == "level_2":
            return cls._level_2(data)
        elif delevel == "level_3":
            return cls._level_3(data)
        return data

    @classmethod
    def _level_1(cls, data: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                value = cls.EMAIL_PATTERN.sub("[EMAIL]", value)
                value = cls.PHONE_PATTERN.sub("[PHONE]", value)
                value = cls._mask_address(value)
                value = cls.NAME_PATTERN.sub("[NAME]", value)
            elif isinstance(value, dict):
                value = cls._level_1(value)
            elif isinstance(value, list):
                value = [cls._level_1(item) if isinstance(item, dict) else item for item in value]
            result[key] = value
        return result

    @classmethod
    def _level_2(cls, data: dict[str, Any]) -> dict[str, Any]:
        result = cls._level_1(data)
        for key, value in result.items():
            if isinstance(value, str):
                value = cls.IP_PATTERN.sub(cls._mask_ip, value)
            elif isinstance(value, dict):
                value = cls._level_2(value)
            elif isinstance(value, list):
                value = [cls._level_2(item) if isinstance(item, dict) else item for item in value]
            result[key] = value
        return result

    @classmethod
    def _level_3(cls, data: dict[str, Any]) -> dict[str, Any]:
        result = cls._level_2(data)
        for key, value in result.items():
            if isinstance(value, str):
                value = hashlib.sha256(value.encode()).hexdigest()[:16]
            elif isinstance(value, dict):
                value = cls._level_3(value)
            elif isinstance(value, list):
                value = [cls._level_3(item) if isinstance(item, dict) else item for item in value]
            result[key] = value
        return result

    @classmethod
    def _mask_ip(cls, match: re.Match) -> str:
        parts = match.group().split(".")
        return f"{parts[0]}.{parts[1]}.xxx.xxx"

    @classmethod
    def _mask_address(cls, text: str) -> str:
        province_pattern = re.compile(r"(北京市|上海市|广州市|深圳市|杭州市|南京市|成都市|武汉市)")
        text = province_pattern.sub("[CITY]", text)
        district_pattern = re.compile(r"[\u4e00-\u9fa5]{2,}区")
        text = district_pattern.sub("[DISTRICT]", text)
        return text