"""Agent Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentExpertise(BaseModel):
    """蒸馏的专家模型：资深开发者的工程偏好与套路。

    所有字段均可选；未填写的字段不会被持久化，也不会注入运行时。
    """

    role_title: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=2000)
    conventions: dict[str, list[str]] | None = None
    review_checklist: list[str] | None = None
    tech_preferences: dict[str, list[str]] | None = None
    anti_patterns: list[str] | None = None
    debugging_heuristics: list[str] | None = None
    communication_style: str | None = Field(default=None, max_length=1000)


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    capabilities: list[str] = Field(default_factory=list)
    model: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)
    expertise: AgentExpertise | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    capabilities: list[str]
    model: str
    status: str
    description: str | None = None
    avatar_url: str | None = None
    expertise: AgentExpertise | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")
    capabilities: list[str] | None = None
    description: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)
    expertise: AgentExpertise | None = None


class ExpertiseExtractRequest(BaseModel):
    """AI 辅助抽取请求：用户提供真实工作素材，抽取成结构化专家模型。"""

    source_text: str = Field(..., min_length=20, max_length=20000,
                             description="代码评审 / 提交记录 / 技术讨论等素材")
    role_hint: str | None = Field(default=None, max_length=200,
                                   description="可选的角色提示，辅助 LLM 定位")
