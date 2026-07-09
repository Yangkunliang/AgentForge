"""Add structured LLM provider credential model route tables

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_providers",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_key", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "provider_key", name="uq_llm_providers_user_provider_key"),
    )
    op.create_index("ix_llm_providers_user_id", "llm_providers", ["user_id"])
    op.create_index("ix_llm_providers_status", "llm_providers", ["status"])

    op.create_table(
        "llm_models",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", sa.String(50), sa.ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_key", sa.String(160), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=True),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("input_price_per_1m", sa.Float(), nullable=True),
        sa.Column("output_price_per_1m", sa.Float(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "model_key", name="uq_llm_models_user_model_key"),
    )
    op.create_index("ix_llm_models_user_id", "llm_models", ["user_id"])
    op.create_index("ix_llm_models_model_key", "llm_models", ["model_key"])
    op.create_index("ix_llm_models_status", "llm_models", ["status"])

    op.create_table(
        "llm_credentials",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", sa.String(50), sa.ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("encrypted_secret", sa.String(4096), nullable=False),
        sa.Column("secret_hint", sa.String(80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_llm_credentials_user_id", "llm_credentials", ["user_id"])
    op.create_index("ix_llm_credentials_active", "llm_credentials", ["active"])

    op.create_table(
        "llm_routes",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("route_key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("provider_id", sa.String(50), sa.ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_id", sa.String(50), sa.ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("credential_id", sa.String(50), sa.ForeignKey("llm_credentials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("fallback_route_keys", sa.JSON(), nullable=True),
        sa.Column("budget_policy", sa.JSON(), nullable=True),
        sa.Column("retry_policy", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "route_key", name="uq_llm_routes_user_route_key"),
    )
    op.create_index("ix_llm_routes_user_id", "llm_routes", ["user_id"])
    op.create_index("ix_llm_routes_route_key", "llm_routes", ["route_key"])
    op.create_index("ix_llm_routes_active", "llm_routes", ["active"])

    op.add_column("pipeline_stage_states", sa.Column("model_route_key", sa.String(80), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("model_route_name", sa.String(120), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("model_name", sa.String(160), nullable=True))
    op.add_column("pipeline_stage_states", sa.Column("model_route_source", sa.String(30), nullable=True))
    op.create_index("ix_pipeline_stage_states_model_route_key", "pipeline_stage_states", ["model_route_key"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_stage_states_model_route_key", table_name="pipeline_stage_states")
    op.drop_column("pipeline_stage_states", "model_route_source")
    op.drop_column("pipeline_stage_states", "model_name")
    op.drop_column("pipeline_stage_states", "model_route_name")
    op.drop_column("pipeline_stage_states", "model_route_key")

    op.drop_index("ix_llm_routes_active", table_name="llm_routes")
    op.drop_index("ix_llm_routes_route_key", table_name="llm_routes")
    op.drop_index("ix_llm_routes_user_id", table_name="llm_routes")
    op.drop_table("llm_routes")
    op.drop_index("ix_llm_credentials_active", table_name="llm_credentials")
    op.drop_index("ix_llm_credentials_user_id", table_name="llm_credentials")
    op.drop_table("llm_credentials")
    op.drop_index("ix_llm_models_status", table_name="llm_models")
    op.drop_index("ix_llm_models_model_key", table_name="llm_models")
    op.drop_index("ix_llm_models_user_id", table_name="llm_models")
    op.drop_table("llm_models")
    op.drop_index("ix_llm_providers_status", table_name="llm_providers")
    op.drop_index("ix_llm_providers_user_id", table_name="llm_providers")
    op.drop_table("llm_providers")
