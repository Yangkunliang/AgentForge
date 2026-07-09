"""Pipeline Catalog routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent_forge.models import User
from agent_forge.pipeline.catalog import (
    get_pipeline_definition,
    list_pipeline_definitions,
    pipeline_definition_to_dict,
)
from middleware.auth import get_current_user

router = APIRouter()


@router.get("/catalog")
async def list_pipeline_catalog(
    current_user: User = Depends(get_current_user),
) -> dict:
    _ = current_user
    return {
        "items": [
            pipeline_definition_to_dict(definition)
            for definition in list_pipeline_definitions()
        ]
    }


@router.get("/catalog/{intent_type}")
async def get_pipeline_catalog_item(
    intent_type: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    _ = current_user
    return pipeline_definition_to_dict(get_pipeline_definition(intent_type))
