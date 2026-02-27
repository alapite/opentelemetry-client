from typing import cast

from primes.distributions.base import DistributionMetadata, DistributionPlugin
from primes.distributions.utils import parse_float


class LinearDistribution(DistributionPlugin):
    """
    Linear ramp-up distribution - gradually increases from 0 to target RPS.

    This distribution linearly interpolates the request rate from 0 to target_rps
    over the specified ramp_duration. After the ramp completes, it maintains the
    target rate.

    Example:
        d = LinearDistribution()
        d.initialize({"ramp_duration": 30.0})
        # At t=0: rate=0
        # At t=15: rate=50% of target_rps
        # At t=30: rate=target_rps
        # At t=60: rate=target_rps (stays constant after ramp)
    """

    ramp_duration: float
    config: dict[str, object]
    _parse_error: bool

    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="linear",
            version="1.0.0",
            description="Linear ramp-up distribution - gradually increases from 0 to target RPS",
            author="primes-client",
            parameters={
                "ramp_duration": {
                    "type": "float",
                    "default": 60.0,
                    "description": "Ramp duration in seconds to reach target RPS",
                    "required": False,
                }
            },
        )

    def initialize(self, config: dict[str, object]) -> None:
        self._parse_error = False
        if "ramp_duration" in config:
            ramp_duration, parsed = parse_float(config.get("ramp_duration"), 60.0)
            if not parsed:
                self._parse_error = True
            self.ramp_duration = cast(float, ramp_duration)
        else:
            self.ramp_duration = 60.0
        self.config = config

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        # Guard against invalid configurations
        if self.ramp_duration <= 0:
            return target_rps

        if time_elapsed >= self.ramp_duration:
            return target_rps

        # Calculate linear ramp-up rate
        return (time_elapsed / self.ramp_duration) * target_rps

    def validate(self) -> bool:
        """Validate the linear distribution configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Validations performed:
            - ramp_duration must be greater than 0
            - config must be a dict if provided
        """
        if self._parse_error:
            return False

        # Check that ramp_duration is positive (prevents division by zero)
        if not self._validate_numeric_param(self.ramp_duration, positive=True):
            return False

        # Validate config structure
        return self._validate_config()
