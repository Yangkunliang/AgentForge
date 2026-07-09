"""Structured LLM provider, credential, model and route models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class LLMProviderSetting(Base, TimestampMixin):
    """A user-scoped LLM provider endpoint."""

    __tablename__ = "llm_providers"
    __table_args__ = (
        UniqueConstraint("user_id", "provider_key", name="uq_llm_providers_user_provider_key"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    models: Mapped[list[LLMModelSetting]] = relationship(back_populates="provider", cascade="all, delete-orphan")
    credentials: Mapped[list[LLMCredential]] = relationship(back_populates="provider", cascade="all, delete-orphan")
    routes: Mapped[list[LLMRoute]] = relationship(back_populates="provider")


class LLMModelSetting(Base, TimestampMixin):
    """A model exposed by a provider."""

    __tablename__ = "llm_models"
    __table_args__ = (
        UniqueConstraint("user_id", "model_key", name="uq_llm_models_user_model_key"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False)
    model_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    context_window: Mapped[int | None] = mapped_column(nullable=True)
    input_price_per_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_price_per_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    provider: Mapped[LLMProviderSetting] = relationship(back_populates="models")
    routes: Mapped[list[LLMRoute]] = relationship(back_populates="model")


class LLMCredential(Base, TimestampMixin):
    """Encrypted LLM credential. Plain secrets are never returned by the API."""

    __tablename__ = "llm_credentials"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(String(4096), nullable=False)
    secret_hint: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    provider: Mapped[LLMProviderSetting] = relationship(back_populates="credentials")
    routes: Mapped[list[LLMRoute]] = relationship(back_populates="credential")


class LLMRoute(Base, TimestampMixin):
    """A named model route used by stages or agents."""

    __tablename__ = "llm_routes"
    __table_args__ = (
        UniqueConstraint("user_id", "route_key", name="uq_llm_routes_user_route_key"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    route_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_id: Mapped[str] = mapped_column(ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False)
    model_id: Mapped[str] = mapped_column(ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False)
    credential_id: Mapped[str | None] = mapped_column(
        ForeignKey("llm_credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    max_tokens: Mapped[int] = mapped_column(nullable=False, default=4096)
    timeout_seconds: Mapped[int] = mapped_column(nullable=False, default=60)
    fallback_route_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    budget_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    retry_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    provider: Mapped[LLMProviderSetting] = relationship(back_populates="routes")
    model: Mapped[LLMModelSetting] = relationship(back_populates="routes")
    credential: Mapped[LLMCredential | None] = relationship(back_populates="routes")
