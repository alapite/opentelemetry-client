import os
from pathlib import Path
from typing import Literal

from primes.distributions.base import (
    DistributionPlugin,
    DistributionMetadata,
    DistributionProtocol,
    Parameter,
)
from primes.distributions.registry import registry
from primes.distributions.loader import (
    load_plugin,
    discover_plugins,
    load_entry_points,
    load_plugins,
)

DistributionType = Literal[
    "constant",
    "linear",
    "poisson",
    "step",
    "sine",
    "sequence",
    "mix",
]

DISTRIBUTIONS_PATH = Path(__file__).parent
DEFAULT_DISTRIBUTION = "constant"

if os.getenv("PRIMES_AUTO_DISCOVER", "").lower() == "true":
    load_plugins()


def register_builtin_distributions() -> None:
    from primes.distributions.constant import ConstantDistribution
    from primes.distributions.linear import LinearDistribution
    from primes.distributions.poisson import PoissonDistribution
    from primes.distributions.step import StepDistribution
    from primes.distributions.sine import SineDistribution
    from primes.distributions.mix import MixDistribution
    from primes.distributions.sequence import SequenceDistribution

    registry.register("constant", ConstantDistribution)
    registry.register("linear", LinearDistribution)
    registry.register("poisson", PoissonDistribution)
    registry.register("step", StepDistribution)
    registry.register("sine", SineDistribution)
    registry.register("mix", MixDistribution)
    registry.register("sequence", SequenceDistribution)

__all__ = [
    "DistributionPlugin",
    "DistributionMetadata",
    "DistributionProtocol",
    "DistributionType",
    "Parameter",
    "DISTRIBUTIONS_PATH",
    "DEFAULT_DISTRIBUTION",
    "registry",
    "load_plugin",
    "discover_plugins",
    "load_entry_points",
    "load_plugins",
    "register_builtin_distributions",
]
