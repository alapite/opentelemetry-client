from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from primes.distributions.base import DistributionPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, type["DistributionPlugin"]] = {}

    def register(self, name: str, plugin_class: type["DistributionPlugin"]) -> None:
        self._plugins[name] = plugin_class

    def get(self, name: str) -> Optional[type["DistributionPlugin"]]:
        return self._plugins.get(name)

    def list_all(self) -> list[str]:
        return list(self._plugins.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._plugins



registry = PluginRegistry()
