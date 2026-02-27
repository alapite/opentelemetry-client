
from primes.distributions.base import DistributionMetadata, DistributionPlugin
from primes.distributions.utils import parse_float


class ConstantDistribution(DistributionPlugin):
    """
    Constant rate distribution - maintains steady request rate throughout test.

    This is the simplest distribution that maintains a constant request rate.
    It can optionally override the target_rps with a fixed rps value if specified.
    """
    _parse_error: bool

    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="constant",
            version="1.0.0",
            description="Constant rate distribution - maintains steady request rate throughout test",
            author="primes-client",
            parameters={
                "rps": {
                    "type": "float",
                    "default": None,
                    "description": "Fixed requests per second (overrides target_rps if set)",
                    "required": False,
                }
            },
        )

    def initialize(self, config: dict[str, object]) -> None:
        self._parse_error = False
        if config and "rps" in config:
            self.rps, parsed = parse_float(config.get("rps"), None)
            if not parsed:
                self._parse_error = True
        else:
            self.rps = None
        self.config = config if config else {}

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        """Return the constant rate (either rps or target_rps).

        Args:
            time_elapsed: Time elapsed since test start (ignored for constant distribution)
            target_rps: Target requests per second to use as fallback

        Returns:
            float: The constant rate to use, either self.rps or target_rps

        Note:
            This method is time-independent for constant distributions.
            Returns target_rps if self.rps is not set or invalid.
        """
        # Use configured RPS if set, otherwise fall back to target_rps
        if self.rps is not None and self.rps > 0:
            return self.rps

        # Fall back to target_rps, ensuring it's non-negative
        return max(0.0, target_rps)

    def validate(self) -> bool:
        """Validate the constant distribution configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Validations performed:
            - rps (if set) must be positive (greater than 0)
            - config must be a dict if provided
        """
        if self._parse_error:
            return False

        # Validate rps parameter
        if not self._validate_numeric_param(self.rps, positive=True):
            return False

        # Validate config structure
        return self._validate_config()
