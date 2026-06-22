"""Agent Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    capabilities: list[str] = Field(default_factory=list)
    model: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)


class AgentResponse(BaseModel):
    id: str
    name: str
    capabilities: list[str]
    model: str
    status: str
    description: str | None = None
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")
    capabilities: list[str] | None = None
    description: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)
