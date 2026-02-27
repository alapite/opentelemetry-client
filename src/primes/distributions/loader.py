import logging
from importlib import import_module
from typing import TYPE_CHECKING

from primes.distributions.registry import registry

if TYPE_CHECKING:
    from primes.distributions.base import DistributionPlugin

logger = logging.getLogger(__name__)


def load_entry_points(group: str) -> dict[str, type]:
    from importlib.metadata import entry_points

    plugins: dict[str, type] = {}
    try:
        eps = entry_points(group=group)
        for ep in eps:
            try:
                value = ep.value
                module_name, class_name = value.rsplit(":", 1)
                module = import_module(module_name)
                plugin_class = getattr(module, class_name)
                plugins[ep.name] = plugin_class
            except Exception as e:
                logger.warning(f"Failed to load entry point {ep.name}: {e}")
    except Exception as e:
        logger.warning(f"Failed to load entry points for group {group}: {e}")
    return plugins


def discover_plugins() -> dict[str, type["DistributionPlugin"]]:
    return load_entry_points("primes.distributions")


def register_plugins(plugins: dict[str, type["DistributionPlugin"]]) -> None:
    for name, plugin_class in plugins.items():
        registry.register(name, plugin_class)


def load_plugin(name: str) -> "DistributionPlugin":
    plugin_class = registry.get(name)
    if plugin_class is None:
        raise ValueError(f"Plugin '{name}' not found in registry")

    return plugin_class()


def get_plugin_class(name: str) -> type["DistributionPlugin"] | None:
    plugin_class = registry.get(name)
    if plugin_class is None:
        from primes.distributions import register_builtin_distributions

        register_builtin_distributions()
        plugin_class = registry.get(name)
    return plugin_class


def instantiate_plugin(
    name: str, config: dict[str, object] | None = None
) -> "DistributionPlugin":
    plugin_class = get_plugin_class(name)
    if plugin_class is None:
        raise ValueError(f"Distribution '{name}' not found")
    instance = plugin_class()
    instance.initialize(config or {})
    return instance


def load_plugins() -> None:
    plugins = discover_plugins()
    register_plugins(plugins)
    logger.info(
        f"Discovered {len(plugins)} distribution plugins: {list(plugins.keys())}"
    )
