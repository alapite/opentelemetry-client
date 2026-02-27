from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from primes.api import config as api_config
from primes.api.presets_store import Preset, PresetsStore

router = APIRouter()


class PresetRequest(BaseModel):
    name: str = Field(..., description="Human-friendly preset name")
    config: dict[str, Any] = Field(..., description="Test configuration")


class PresetResponse(BaseModel):
    id: str
    name: str
    config: dict[str, Any]


def _get_store() -> PresetsStore:
    return PresetsStore(Path(api_config.PRESETS_FILE))


def _to_response(preset: Preset) -> PresetResponse:
    return PresetResponse(id=preset.id, name=preset.name, config=preset.config)


@router.get("/presets", response_model=list[PresetResponse])
async def list_presets() -> list[PresetResponse]:
    store = _get_store()
    return [_to_response(preset) for preset in store.list_presets()]


@router.post(
    "/presets",
    response_model=PresetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_preset(request: PresetRequest) -> PresetResponse:
    store = _get_store()
    try:
        preset = store.create_preset(name=request.name, config=request.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(preset)


@router.put("/presets/{preset_id}", response_model=PresetResponse)
async def update_preset(preset_id: str, request: PresetRequest) -> PresetResponse:
    store = _get_store()
    try:
        preset = store.update_preset(
            preset_id,
            name=request.name,
            config=request.config,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(preset)


@router.delete("/presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(preset_id: str) -> None:
    store = _get_store()
    try:
        store.delete_preset(preset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
