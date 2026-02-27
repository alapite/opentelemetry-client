from typing import Optional, cast
import math

from primes.distributions.base import DistributionMetadata, DistributionPlugin
from primes.distributions.utils import parse_float


class SineDistribution(DistributionPlugin):
    """
    Sine wave distribution - periodic rate modulation following sine pattern.

    This distribution provides smooth, periodic oscillation around a base rate,
    simulating realistic traffic patterns that exhibit periodicity (e.g., daily cycles,
    hourly variations). The sine wave provides predictable oscillation with configurable
    period, amplitude, and phase shift.

    Example:
        d = SineDistribution()
        d.initialize({"period": 3600.0, "amplitude": 0.5})
        # At t=0: rate = base * (1 + 0.5 * sin(0)) = base
        # At t=900 (1/4 period): rate = base * (1 + 0.5 * sin(pi/2)) = base * 1.5
        # At t=1800 (1/2 period): rate = base * (1 + 0.5 * sin(pi)) = base
        # At t=2700 (3/4 period): rate = base * (1 + 0.5 * sin(3pi/2)) = base * 0.5
        # At t=3600 (full period): rate = base * (1 + 0.5 * sin(2pi)) = base
    """

    period: float
    amplitude: float
    phase_shift: float
    base_rps: Optional[float]
    config: dict[str, object]
    _parse_error: bool

    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="sine",
            version="1.0.0",
            description="Sine wave distribution - periodic rate modulation following sine pattern",
            author="primes-client",
            parameters={
                "period": {
                    "type": "float",
                    "default": 3600.0,
                    "description": "Period in seconds (default 1 hour)",
                    "required": False,
                },
                "amplitude": {
                    "type": "float",
                    "default": 0.5,
                    "description": "Amplitude as fraction of target RPS (0-1)",
                    "required": False,
                },
                "phase_shift": {
                    "type": "float",
                    "default": 0.0,
                    "description": "Phase shift in seconds",
                    "required": False,
                },
                "base_rps": {
                    "type": "float",
                    "default": None,
                    "description": "Base rate (uses target_rps if not set)",
                    "required": False,
                },
            },
        )

    def _parse_required_float(
        self, config: dict[str, object], key: str, default: float
    ) -> float:
        if key not in config:
            return default
        value, parsed = parse_float(config.get(key), default)
        if not parsed:
            self._parse_error = True
        return cast(float, value)

    def _parse_optional_float(
        self, config: dict[str, object], key: str
    ) -> Optional[float]:
        if key not in config:
            return None
        value, parsed = parse_float(config.get(key), None)
        if not parsed:
            self._parse_error = True
        return value

    def initialize(self, config: dict[str, object]) -> None:
        """Initialize the sine distribution with configuration."""
        self._parse_error = False
        self.period = self._parse_required_float(config, "period", 3600.0)
        self.amplitude = self._parse_required_float(config, "amplitude", 0.5)
        self.phase_shift = self._parse_required_float(config, "phase_shift", 0.0)
        self.base_rps = self._parse_optional_float(config, "base_rps")
        self.config = config if config else {}

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        """Get the current rate based on sine wave modulation."""
        # Guard against division by zero from invalid period
        if self.period <= 0:
            return target_rps

        base = self.base_rps if self.base_rps else target_rps
        angle = 2.0 * math.pi * (time_elapsed + self.phase_shift) / self.period
        return base * (1.0 + self.amplitude * math.sin(angle))

    def validate(self) -> bool:
        """Validate the sine distribution configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Validations performed:
            - period must be greater than 0 (prevents division by zero)
            - amplitude must be between 0 and 1 (exclusive of 0, inclusive of 1)
            - phase_shift must be non-negative
            - base_rps (if set) must be positive
            - config must be a dict if provided
        """
        if self._parse_error:
            return False

        # Check that period is positive (prevents division by zero)
        if not self._validate_numeric_param(
            self.period, positive=True, allow_none=False
        ):
            return False

        # Amplitude must be between 0 and 1 (exclusive of 0, inclusive of 1)
        if not self._validate_numeric_param(
            self.amplitude, positive=True, allow_none=False
        ) or not (0 < self.amplitude <= 1):
            return False

        # Phase shift must be non-negative
        if not self._validate_numeric_param(
            self.phase_shift, non_negative=True, allow_none=False
        ):
            return False

        # Base RPS (if set) must be positive
        if not self._validate_numeric_param(self.base_rps, positive=True):
            return False

        # Validate config structure
        return self._validate_config()
