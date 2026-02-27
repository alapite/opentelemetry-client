from typing import cast

from primes.distributions.base import DistributionMetadata, DistributionPlugin
from primes.distributions.utils import parse_float, parse_json_or_list


class StepDistribution(DistributionPlugin):
    """
    Step distribution - sudden rate changes at specified times.

    This distribution provides piecewise constant rate with sudden changes at
    specified time points. Useful for simulating burst traffic, scheduled events,
    or testing system behavior under abrupt load changes.

    Configuration format:
        steps: JSON array of [time_seconds, rps] pairs
               Example: "[[10, 50], [30, 100], [60, 75]]"
        default_rps: Rate to use before first step (default: 0.0)

    Example:
        d = StepDistribution()
        d.initialize({"steps": "[[10, 50], [30, 100]]", "default_rps": 10})
        # t=5: rate=10 (default)
        # t=10: rate=50 (first step)
        # t=20: rate=50 (continues until next step)
        # t=30: rate=100 (second step)
    """

    steps: list[tuple[float, float]]
    default_rps: float
    config: dict[str, object]
    _parse_error: bool

    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="step",
            version="1.0.0",
            description="Step distribution - sudden rate changes at specified times",
            author="primes-client",
            parameters={
                "steps": {
                    "type": "str",
                    "default": None,
                    "description": "JSON array of [time, rps] pairs for step transitions",
                    "required": False,
                },
                "default_rps": {
                    "type": "float",
                    "default": 0.0,
                    "description": "Rate to use before first step (default: 0.0)",
                    "required": False,
                },
            },
        )

    def _parse_steps(self, steps_json: object) -> list[tuple[float, float]]:
        if not steps_json:
            return []
        success, steps_data = parse_json_or_list(steps_json)
        if not success or not isinstance(steps_data, list):
            self._parse_error = True
            return []
        try:
            return sorted((float(t), float(r)) for t, r in steps_data)
        except (ValueError, TypeError):
            self._parse_error = True
            return []

    def _is_valid_step(self, step: object, prev_time: float) -> tuple[bool, float]:
        if not isinstance(step, (list, tuple)) or len(step) != 2:
            return False, prev_time

        step_time, step_rate = step
        if not self._validate_numeric_param(
            step_time, non_negative=True, allow_none=False
        ):
            return False, prev_time
        if not self._validate_numeric_param(
            step_rate, non_negative=True, allow_none=False
        ):
            return False, prev_time
        if step_time <= prev_time:
            return False, prev_time
        return True, step_time

    def initialize(self, config: dict[str, object]) -> None:
        """Initialize the step distribution with configuration."""
        self._parse_error = False
        if "default_rps" in config:
            default_rps, parsed = parse_float(config.get("default_rps"), 0.0)
            if not parsed:
                self._parse_error = True
            self.default_rps = cast(float, default_rps)
        else:
            self.default_rps = 0.0

        self.steps = self._parse_steps(config.get("steps"))
        self.config = config

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        """Get the current rate based on elapsed time and step configuration.

        Args:
            time_elapsed: Time elapsed since test start in seconds
            target_rps: Target requests per second to use as fallback

        Returns:
            float: The rate for the current time step

        Note:
            Returns default_rps before the first step time.
            Steps are applied in order based on their time values.
            If no steps are configured, returns target_rps.
        """
        # Guard against parse errors or invalid configuration
        if self._parse_error:
            return max(0.0, target_rps)

        # If no steps configured, fall back to target_rps
        if not self.steps:
            return max(0.0, target_rps)

        # Start with default rate
        rate = self.default_rps

        # Apply each step in order (steps are sorted by time)
        for step_time, step_rate in self.steps:
            if step_time <= time_elapsed:
                rate = step_rate
            else:
                break

        # Ensure rate is never negative
        return max(0.0, rate)

    def validate(self) -> bool:
        """Validate the step distribution configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Validations performed:
            - No parse errors in step configuration
            - default_rps must be non-negative (allows 0)
            - Steps must be a list of tuples with exactly 2 elements
            - Step times must be non-negative
            - Step rates must be non-negative
            - Steps must be sorted by time in ascending order
            - Step times must be unique (no duplicate times)
            - config must be a dict if provided
        """
        # Check for parse errors from JSON or type conversion
        if self._parse_error:
            return False

        # Validate default_rps
        if not self._validate_numeric_param(
            self.default_rps, non_negative=True, allow_none=False
        ):
            return False

        if self.steps and not isinstance(self.steps, list):
            return False

        prev_time = -1.0
        for step in self.steps:
            valid, prev_time = self._is_valid_step(step, prev_time)
            if not valid:
                return False

        # Validate config structure
        return self._validate_config()
