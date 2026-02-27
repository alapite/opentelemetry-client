from primes.distributions.constant import ConstantDistribution
from primes.distributions.linear import LinearDistribution


class TestValidateConfigHelper:
    def test_validates_dict_config(self):
        dist = ConstantDistribution()
        dist.initialize({"rps": 10.0})
        assert dist._validate_config() is True

    def test_validates_none_config(self):
        dist = ConstantDistribution()
        dist.initialize(None)
        assert dist._validate_config() is True

    def test_rejects_invalid_config(self):
        dist = ConstantDistribution()
        dist.initialize({})
        dist.config = "invalid"  # Manually set invalid config
        assert dist._validate_config() is False


class TestValidateNumericParamHelper:
    def test_validates_positive_param(self):
        dist = ConstantDistribution()
        dist.initialize({"rps": 10.0})
        assert dist._validate_numeric_param(dist.rps, positive=True) is True

    def test_rejects_zero_for_positive(self):
        dist = ConstantDistribution()
        dist.initialize({"rps": 0.0})
        assert dist._validate_numeric_param(dist.rps, positive=True) is False

    def test_validates_non_negative_param(self):
        dist = LinearDistribution()
        dist.initialize({"ramp_duration": 60.0})
        assert (
            dist._validate_numeric_param(dist.ramp_duration, non_negative=True) is True
        )

    def test_rejects_negative_for_non_negative(self):
        dist = LinearDistribution()
        dist.initialize({"ramp_duration": -10.0})
        assert (
            dist._validate_numeric_param(dist.ramp_duration, non_negative=True) is False
        )

    def test_allows_none_by_default(self):
        dist = ConstantDistribution()
        dist.initialize({})
        assert dist._validate_numeric_param(dist.rps) is True

    def test_rejects_none_when_specified(self):
        dist = ConstantDistribution()
        dist.initialize({})
        assert dist._validate_numeric_param(dist.rps, allow_none=False) is False
