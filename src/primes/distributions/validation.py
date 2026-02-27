import json
from typing import Any

from primes.distributions.loader import get_plugin_class


def normalize_distribution_config(name: str, config: dict[str, Any]) -> dict[str, Any]:
    if name == "mix":
        return _normalize_list_field(config, "components")
    if name == "sequence":
        return _normalize_list_field(config, "stages")
    return config


def validate_distribution_config(
    name: str, config: dict[str, Any], path: str = "config"
) -> list[str]:
    plugin_class = get_plugin_class(name)
    if plugin_class is None:
        return [f"{path}.name '{name}' not found"]

    errors: list[str] = []
    if name == "mix":
        errors.extend(_validate_mix_config(config))
    elif name == "sequence":
        errors.extend(_validate_sequence_config(config))

    if errors:
        return errors

    instance = plugin_class()
    instance.initialize(config)
    if not instance.validate():
        errors.append(f"{path} validation failed")
    return errors


def _normalize_list_field(config: dict[str, Any], field_name: str) -> dict[str, Any]:
    if field_name not in config:
        return config

    value = config[field_name]
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            raise ValueError(f"{field_name} must be a JSON array or list")

    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")

    config[field_name] = value
    return config


def _distribution_errors(
    container: dict[str, Any], index: int, parent_field: str
) -> list[str]:
    errors: list[str] = []
    distribution = container.get("distribution")
    if not isinstance(distribution, dict):
        return [f"{parent_field}[{index}].distribution must be an object"]

    name = distribution.get("name")
    if not isinstance(name, str) or not name:
        return [f"{parent_field}[{index}].distribution.name is required"]

    config_value = distribution.get("config", {})
    if config_value is None:
        config_value = {}
    if not isinstance(config_value, dict):
        return [f"{parent_field}[{index}].distribution.config must be an object"]

    nested_config = normalize_distribution_config(name, dict(config_value))
    errors.extend(
        validate_distribution_config(
            name, nested_config, f"{parent_field}[{index}].distribution"
        )
    )
    return errors


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and value > 0


def _validate_mix_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    components = config.get("components")
    if not isinstance(components, list) or not components:
        return ["components must be a non-empty list"]

    for index, component in enumerate(components):
        if not isinstance(component, dict):
            errors.append(f"components[{index}] must be an object")
            continue
        if not _is_positive_number(component.get("weight")):
            errors.append(f"components[{index}].weight must be > 0")
        errors.extend(_distribution_errors(component, index, "components"))

    return errors


def _validate_sequence_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stages = config.get("stages")
    if not isinstance(stages, list) or not stages:
        return ["stages must be a non-empty list"]

    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            errors.append(f"stages[{index}] must be an object")
            continue
        if not _is_positive_number(stage.get("duration_seconds")):
            errors.append(f"stages[{index}].duration_seconds must be > 0")
        errors.extend(_distribution_errors(stage, index, "stages"))

    post_behavior = config.get("post_behavior")
    if post_behavior is not None and post_behavior not in {
        "hold_last",
        "zero",
        "repeat",
    }:
        errors.append("post_behavior must be one of: hold_last, zero, repeat")

    return errors
