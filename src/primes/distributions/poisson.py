from typing import Optional, cast

from primes.distributions.base import DistributionMetadata, DistributionPlugin
from primes.distributions.utils import parse_float


class PoissonDistribution(DistributionPlugin):
    """
    Poisson distribution - random arrivals with controlled average rate.

    Simulates realistic traffic where requests arrive randomly but with a controlled
    average rate. Uses Gaussian noise to modulate the rate around the target, creating
    realistic variation while maintaining the desired average.

    Example:
        d = PoissonDistribution()
        d.initialize({"lambda_param": 50.0, "variance_scale": 1.0})
        # Returns rates around 50 RPS with 10% variance
    """

    lambda_param: Optional[float]
    variance_scale: float
    config: dict[str, object]
    _parse_error: bool

    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="poisson",
            version="1.0.0",
            description="Poisson distribution - random arrivals with controlled average rate",
            author="primes-client",
            parameters={
                "lambda_param": {
                    "type": "float",
                    "default": None,
                    "description": "Average requests per second (uses target_rps if not set)",
                    "required": False,
                },
                "variance_scale": {
                    "type": "float",
                    "default": 1.0,
                    "description": "Scale factor for variance (1.0 = standard Poisson)",
                    "required": False,
                },
            },
        )

    def initialize(self, config: dict[str, object]) -> None:
        self._parse_error = False
        if config and "lambda_param" in config:
            self.lambda_param, parsed = parse_float(config.get("lambda_param"), None)
            if not parsed:
                self._parse_error = True
        else:
            self.lambda_param = None

        if "variance_scale" in config:
            variance_scale, parsed = parse_float(config.get("variance_scale"), 1.0)
            if not parsed:
                self._parse_error = True
            self.variance_scale = cast(float, variance_scale)
        else:
            self.variance_scale = 1.0
        self.config = config if config else {}

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        """Get the current rate based on Poisson distribution with Gaussian noise.

        Args:
            time_elapsed: Time elapsed since test start (ignored for Poisson distribution)
            target_rps: Target requests per second to use if lambda_param is not set

        Returns:
            float: The rate for this time step, always non-negative

        Note:
            This method uses Gaussian noise to introduce realistic variance around
            the mean rate. The actual rate can vary between approximately
            0 and 2x the mean rate.
        """
        import random

        # Use lambda_param if set, otherwise fall back to target_rps
        effective = self.lambda_param if self.lambda_param else target_rps

        # Guard against negative or invalid effective rates
        if effective <= 0:
            return 0.0

        # Add Gaussian noise for realistic variation
        # Noise has standard deviation of 10% * variance_scale
        noise = random.gauss(0, 0.1 * self.variance_scale)

        # Ensure rate is never negative
        return max(0.0, effective * (1 + noise))

    def validate(self) -> bool:
        """Validate the Poisson distribution configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Validations performed:
            - lambda_param (if set) must be positive (greater than 0)
            - lambda_param (if set) must be a finite number (not NaN or infinity)
            - variance_scale must be greater than 0
            - variance_scale must be a finite number (not NaN or infinity)
            - config must be a dict if provided
        """
        if self._parse_error:
            return False

        # Validate lambda_param if set
        if not self._validate_numeric_param(self.lambda_param, positive=True):
            return False

        # Validate variance_scale (required, must be positive)
        if not self._validate_numeric_param(
            self.variance_scale, positive=True, allow_none=False
        ):
            return False

        # Validate config structure
        return self._validate_config()
