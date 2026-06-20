"""Harness Layer 1: Validator - 输入验证和 Prompt 注入防护"""

from __future__ import annotations

import logging
import re

from pydantic import ValidationError

logger = logging.getLogger("agent_forge.harness.validator")


# Prompt 注入检测关键词黑名单
PROMPT_INJECTION_BLACKLIST = [
    "system:",
    "ignore previous",
    "ignore all",
    "forget everything",
    "disregard",
    "override",
    "bypass",
    "new instructions",
    "stop following",
    "ignore instructions",
    "忽略",
    "无视",
    "覆盖",
    "绕过",
    "新指令",
]


class ValidationResult:
    """验证结果"""

    def __init__(
        self,
        is_valid: bool,
        sanitized_input: str | None = None,
        errors: list[str] | None = None,
    ):
        self.is_valid = is_valid
        self.sanitized_input = sanitized_input
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.is_valid


class Validator:
    """输入验证器"""

    MAX_DESCRIPTION_LENGTH = 500

    def validate_description(self, description: str) -> ValidationResult:
        """验证任务描述"""
        errors = []

        # 1. 长度限制
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(f"Description exceeds maximum length ({self.MAX_DESCRIPTION_LENGTH} characters)")

        # 2. Prompt 注入检测
        injection_detected = self._detect_prompt_injection(description)
        if injection_detected:
            errors.append(f"Prompt injection detected: {injection_detected}")
            logger.warning(f"Prompt injection attempt detected: {description[:100]}")

        # 3. 用户输入隔离
        sanitized_input = self._sanitize_input(description)

        if errors:
            return ValidationResult(
                is_valid=False,
                sanitized_input=sanitized_input,
                errors=errors,
            )

        return ValidationResult(
            is_valid=True,
            sanitized_input=sanitized_input,
        )

    def validate_priority(self, priority: str) -> ValidationResult:
        """验证任务优先级"""
        valid_priorities = ["low", "medium", "high"]

        if priority not in valid_priorities:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid priority: {priority}. Must be one of {valid_priorities}"],
            )

        return ValidationResult(is_valid=True)

    def validate_task_create_request(self, request_data: dict) -> ValidationResult:
        """验证任务创建请求"""
        errors = []

        # 1. Pydantic Schema 二次校验（这里简化处理）
        if "description" not in request_data:
            errors.append("Missing required field: description")
        else:
            desc_result = self.validate_description(request_data["description"])
            if not desc_result.is_valid:
                errors.extend(desc_result.errors)
                request_data["description"] = desc_result.sanitized_input

        if "priority" not in request_data:
            errors.append("Missing required field: priority")
        else:
            priority_result = self.validate_priority(request_data["priority"])
            if not priority_result.is_valid:
                errors.extend(priority_result.errors)

        if errors:
            return ValidationResult(
                is_valid=False,
                sanitized_input=request_data.get("description"),
                errors=errors,
            )

        return ValidationResult(
            is_valid=True,
            sanitized_input=request_data.get("description"),
        )

    def _detect_prompt_injection(self, text: str) -> str | None:
        """检测 Prompt 注入"""
        text_lower = text.lower()

        for keyword in PROMPT_INJECTION_BLACKLIST:
            if keyword.lower() in text_lower:
                return keyword

        # 检测其他常见注入模式
        patterns = [
            r"ignore\s+all\s+previous",
            r"forget\s+everything",
            r"new\s+instructions:",
            r"stop\s+following\s+instructions",
        ]

        for pattern in patterns:
            if re.search(pattern, text_lower):
                return pattern

        return None

    def _sanitize_input(self, text: str) -> str:
        """用户输入隔离（包裹在 <user_input> 标签中）"""
        # 移除可能的注入关键词
        sanitized = text
        for keyword in PROMPT_INJECTION_BLACKLIST:
            sanitized = sanitized.replace(keyword, "")

        # 包裹在 user_input 标签中
        return f"<user_input>{sanitized}</user_input>"


def validate_task_request(request_data: dict) -> ValidationResult:
    """验证任务请求（便捷函数）"""
    validator = Validator()
    return validator.validate_task_create_request(request_data)