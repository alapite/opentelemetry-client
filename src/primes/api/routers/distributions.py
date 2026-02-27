from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from primes.distributions import registry
from primes.distributions.loader import get_plugin_class, instantiate_plugin
from primes.distributions.validation import (
    normalize_distribution_config,
    validate_distribution_config,
)

router = APIRouter()


class ValidateConfigRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class ValidateConfigResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class InstantiateResponse(BaseModel):
    plugin_name: str
    instance_id: str


@router.get("/distributions")
async def list_distributions() -> list[str]:
    return registry.list_all()


@router.post("/distributions/{name}/validate", response_model=ValidateConfigResponse)
async def validate_distribution(
    name: str, request: ValidateConfigRequest
) -> ValidateConfigResponse:
    plugin_class = get_plugin_class(name)
    if plugin_class is None:
        raise HTTPException(status_code=404, detail=f"Distribution '{name}' not found")

    try:
        config = normalize_distribution_config(name, dict(request.config))
        errors = validate_distribution_config(name, config, "config")
        return ValidateConfigResponse(valid=not errors, errors=errors)
    except Exception as e:
        return ValidateConfigResponse(valid=False, errors=[str(e)])


@router.post("/distributions/{name}/instantiate", response_model=InstantiateResponse)
async def instantiate_distribution(name: str) -> InstantiateResponse:
    try:
        instance = instantiate_plugin(name)
        instance_id = f"{name}-{id(instance)}"
        return InstantiateResponse(plugin_name=name, instance_id=instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to instantiate: {e}")
