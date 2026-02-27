from typing import Any, Optional

from primes.distributions.base import DistributionMetadata, DistributionPlugin
from primes.distributions.loader import get_plugin_class
from primes.distributions.utils import to_float, parse_json_or_list


class MixDistribution(DistributionPlugin):
    """
    Mix distribution - weighted sum of multiple distributions.

    Components are combined using normalized weights. Each component can optionally
    override target_rps in its config. The mix can also define a target_rps that
    becomes the default for all components.
    """

    components: list[dict[str, object]]
    mix_target_rps: Optional[float]
    config: dict[str, object]
    _component_plugins: list[DistributionPlugin]
    _component_weights: list[float]
    _component_targets: list[Optional[float]]
    _normalized_weights: list[float]
    _parse_error: bool

    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="mix",
            version="1.0.0",
            description="Mix distribution - weighted sum of multiple distributions",
            author="primes-client",
            parameters={
                "components": {
                    "type": "str",
                    "default": None,
                    "description": "JSON array of {weight, distribution{name, config}}",
                    "required": True,
                },
                "target_rps": {
                    "type": "float",
                    "default": None,
                    "description": "Default target RPS for all components",
                    "required": False,
                },
            },
        )

    def _set_mix_target_rps(self) -> None:
        target_value: Any = self.config.get("target_rps") if self.config else None
        self.mix_target_rps = to_float(target_value, None)
        if target_value is not None and self.mix_target_rps is None:
            self._parse_error = True

    def _parse_components(self) -> Optional[list[object]]:
        components_value = self.config.get("components")
        if components_value is None:
            return []
        success, components_data = parse_json_or_list(components_value)
        if not success or not isinstance(components_data, list):
            self._parse_error = True
            return None
        return components_data

    def _parse_single_component(
        self, component: object
    ) -> Optional[tuple[dict[str, object], DistributionPlugin, float, Optional[float]]]:
        if not isinstance(component, dict):
            self._parse_error = True
            return None

        weight = to_float(component.get("weight"), None)
        if weight is None:
            self._parse_error = True
            return None

        distribution_value = component.get("distribution")
        if not isinstance(distribution_value, dict):
            self._parse_error = True
            return None

        name_value = distribution_value.get("name")
        if not isinstance(name_value, str):
            self._parse_error = True
            return None

        plugin_class = get_plugin_class(name_value)
        if plugin_class is None:
            self._parse_error = True
            return None

        config_value = distribution_value.get("config")
        if config_value is None:
            component_config: dict[str, object] = {}
        elif isinstance(config_value, dict):
            component_config = config_value
        else:
            self._parse_error = True
            return None

        target_override = to_float(component_config.get("target_rps"), None)
        if component_config.get("target_rps") is not None and target_override is None:
            self._parse_error = True
            return None

        plugin_instance = plugin_class()
        plugin_instance.initialize(component_config)
        return component, plugin_instance, weight, target_override

    def _set_normalized_weights(self) -> None:
        total_weight = sum(self._component_weights)
        if total_weight <= 0:
            return
        self._normalized_weights = [
            weight / total_weight for weight in self._component_weights
        ]

    def _effective_target(self, override: Optional[float], target_rps: float) -> float:
        if override is not None:
            return override
        if self.mix_target_rps is not None:
            return self.mix_target_rps
        return target_rps

    def initialize(self, config: dict[str, object]) -> None:
        self.config = config if config else {}
        self._parse_error = False
        self.components = []
        self._component_plugins = []
        self._component_weights = []
        self._component_targets = []
        self._normalized_weights = []
        self._set_mix_target_rps()

        components_data = self._parse_components()
        if components_data is None:
            return

        for component in components_data:
            parsed_component = self._parse_single_component(component)
            if parsed_component is None:
                continue
            raw_component, plugin_instance, weight, target_override = parsed_component
            self.components.append(raw_component)
            self._component_plugins.append(plugin_instance)
            self._component_weights.append(weight)
            self._component_targets.append(target_override)

        self._set_normalized_weights()

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        """Get the current rate as weighted sum of component distributions.

        Args:
            time_elapsed: Time elapsed since test start in seconds
            target_rps: Target requests per second to use as fallback

        Returns:
            float: The weighted sum of all component rates

        Note:
            Each component's rate is multiplied by its normalized weight.
            The final rate is the sum of all weighted component rates.
            Returns target_rps if configuration is invalid.
        """
        # Guard against parse errors or invalid configuration
        if (
            self._parse_error
            or not self._component_plugins
            or not self._normalized_weights
        ):
            return max(0.0, target_rps)

        # Guard against division by zero in normalized_weights
        total_weight = sum(self._normalized_weights)
        if total_weight <= 0:
            return max(0.0, target_rps)

        mixed_rate = 0.0
        for plugin, weight, override in zip(
            self._component_plugins,
            self._normalized_weights,
            self._component_targets,
        ):
            effective_target = self._effective_target(override, target_rps)
            # Get component rate and apply weight
            component_rate = plugin.get_rate(time_elapsed, effective_target)
            mixed_rate += weight * component_rate

        # Ensure rate is never negative
        return max(0.0, mixed_rate)

    def validate(self) -> bool:
        """Validate the mix distribution configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Validations performed:
            - No parse errors in component configuration
            - At least one component is configured
            - mix_target_rps (if set) must be positive
            - All component weights must be positive
            - All component target overrides (if set) must be positive
            - All component plugins must be valid
            - Sum of component weights must be greater than 0
            - All weights and rates must be finite numbers
            - config must be a dict if provided
        """
        # Check for parse errors from JSON or type conversion
        if self._parse_error:
            return False

        # Must have at least one component
        if not self._component_plugins:
            return False

        # Validate mix_target_rps if set
        if not self._validate_numeric_param(self.mix_target_rps, positive=True):
            return False

        for weight, target_override, plugin in zip(
            self._component_weights, self._component_targets, self._component_plugins
        ):
            if not self._validate_numeric_param(
                weight, positive=True, allow_none=False
            ):
                return False
            if not self._validate_numeric_param(target_override, positive=True):
                return False
            if not plugin.validate():
                return False

        # Check that total weight is greater than 0 (prevents division by zero)
        if not self._normalized_weights:
            return False
        total_weight = sum(self._normalized_weights)
        if not self._validate_numeric_param(
            total_weight, positive=True, allow_none=False
        ):
            return False

        # Validate config structure
        return self._validate_config()
