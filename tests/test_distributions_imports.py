from primes.distributions.constant import ConstantDistribution
from primes.distributions.linear import LinearDistribution
from primes.distributions.poisson import PoissonDistribution
from primes.distributions.step import StepDistribution
from primes.distributions.sine import SineDistribution
from primes.distributions.mix import MixDistribution
from primes.distributions.sequence import SequenceDistribution


def test_distribution_modules_importable():
    assert ConstantDistribution.__name__ == "ConstantDistribution"
    assert LinearDistribution.__name__ == "LinearDistribution"
    assert PoissonDistribution.__name__ == "PoissonDistribution"
    assert StepDistribution.__name__ == "StepDistribution"
    assert SineDistribution.__name__ == "SineDistribution"
    assert MixDistribution.__name__ == "MixDistribution"
    assert SequenceDistribution.__name__ == "SequenceDistribution"
