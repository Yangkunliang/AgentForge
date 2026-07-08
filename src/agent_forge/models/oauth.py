"""OAuth state and encrypted credential models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import JSON_VARIANT, Base, TimestampMixin


class OAuthCredential(Base, TimestampMixin):
    """Encrypted external OAuth credential owned by a user."""

    __tablename__ = "oauth_credentials"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    scopes_json: list[str] = Column("scopes", JSON_VARIANT, nullable=False, default=list)
    metadata_json: dict = Column("metadata", JSON_VARIANT, nullable=True, default=dict)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OAuthState(Base, TimestampMixin):
    """Short-lived OAuth state bound to user and project."""

    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: dict = Column("metadata", JSON_VARIANT, nullable=True, default=dict)
