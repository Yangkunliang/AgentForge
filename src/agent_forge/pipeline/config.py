"""Backward-compatible imports for pipeline stage configuration."""

from __future__ import annotations

from agent_forge.pipeline.catalog import (
    PIPELINE_CATALOG,
    IntentType,
    StageDefinition as StageConfig,
    normalize_intent,
)

PIPELINE_CONFIGS: dict[IntentType, list[StageConfig]] = {
    intent_type: list(definition.stages)
    for intent_type, definition in PIPELINE_CATALOG.items()
}
