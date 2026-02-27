from abc import ABC, abstractmethod
from typing import Any, Literal, TypedDict, Protocol, runtime_checkable, Optional

from primes.distributions.utils import validate_numeric, validate_config_structure


class Parameter(TypedDict):
    type: Literal["int", "float", "str", "bool"]
    default: Any
    description: str
    required: bool


class DistributionMetadata(TypedDict):
    name: str
    version: str
    description: str
    author: str
    parameters: dict[str, Parameter]


class DistributionPlugin(ABC):
    @property
    @abstractmethod
    def metadata(self) -> DistributionMetadata:
        raise NotImplementedError

    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        raise NotImplementedError

    @abstractmethod
    def validate(self) -> bool:
        raise NotImplementedError

    def _validate_config(self) -> bool:
        """
        Default config structure validation.

        Validates that the config attribute (if present) is a dict.
        Subclasses can override for custom validation logic.

        Returns:
            bool: True if config is None or a dict, False otherwise
        """
        if not hasattr(self, "config"):
            return True
        return validate_config_structure(self.config)

    def _validate_numeric_param(
        self,
        value: Optional[float],
        *,
        positive: bool = False,
        non_negative: bool = False,
        allow_none: bool = True,
    ) -> bool:
        """
        Convenience wrapper for numeric parameter validation.

        Provides a simplified interface to validate_numeric for use
        in distribution plugin validate() methods.

        Args:
            value: The numeric value to validate
            positive: If True, value must be > 0
            non_negative: If True, value must be >= 0
            allow_none: If True, None values are considered valid

        Returns:
            bool: True if value passes all specified validations

        Examples:
            >>> dist = ConstantDistribution()
            >>> dist.initialize({"rps": 10.0})
            >>> dist._validate_numeric_param(dist.rps, positive=True)
            True
        """
        return validate_numeric(
            value,
            allow_none=allow_none,
            positive=positive,
            non_negative=non_negative,
            finite=True,
        )


@runtime_checkable
class DistributionProtocol(Protocol):
    metadata: DistributionMetadata

    def get_rate(self, time_elapsed: float, target_rps: float) -> float: ...
