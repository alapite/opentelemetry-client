from fastapi import APIRouter, HTTPException

from primes.distributions import registry
from primes.distributions.base import DistributionMetadata, Parameter

router = APIRouter()


class PluginParameterResponse(Parameter):
    pass


class PluginInfoResponse(DistributionMetadata):
    pass


class PluginDetailResponse(DistributionMetadata):
    pass


@router.get("/plugins")
async def list_plugins() -> list[PluginInfoResponse]:
    plugins = []
    for name in registry.list_all():
        plugin_class = registry.get(name)
        if plugin_class:
            instance = plugin_class()
            if hasattr(instance, "metadata"):
                plugins.append(instance.metadata)
    return plugins


@router.get("/plugins/{name}")
async def get_plugin(name: str) -> PluginDetailResponse:
    plugin_class = registry.get(name)
    if plugin_class is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    instance = plugin_class()
    if not hasattr(instance, "metadata"):
        raise HTTPException(status_code=500, detail="Plugin missing metadata")

    return instance.metadata


@router.get("/plugins/{name}/parameters")
async def get_plugin_parameters(name: str) -> dict[str, PluginParameterResponse]:
    plugin_class = registry.get(name)
    if plugin_class is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    instance = plugin_class()
    if not hasattr(instance, "metadata"):
        raise HTTPException(status_code=500, detail="Plugin missing metadata")

    return instance.metadata.get("parameters", {})
