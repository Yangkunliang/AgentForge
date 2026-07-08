"""Artifact domain helpers."""

from .service import (
    ARTIFACT_TYPES,
    create_stage_artifact,
    infer_stage_artifact_type,
)

__all__ = [
    "ARTIFACT_TYPES",
    "create_stage_artifact",
    "infer_stage_artifact_type",
]
