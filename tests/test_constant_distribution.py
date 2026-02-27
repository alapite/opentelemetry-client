from primes.distributions.constant import ConstantDistribution
from tests.distribution_test_utils import distribution_fixture

distribution = distribution_fixture(ConstantDistribution)


class TestConstantDistributionGetRate:
    def test_get_rate_returns_target_rps_when_no_rps_set(self, distribution):
        distribution.initialize({})
        rate = distribution.get_rate(10.0, 100.0)
        assert rate == 100.0

    def test_get_rate_returns_rps_when_set(self, distribution):
        distribution.initialize({"rps": 50.0})
        rate = distribution.get_rate(10.0, 100.0)
        assert rate == 50.0

    def test_get_rate_ignores_time_elapsed(self, distribution):
        distribution.initialize({})
        rate1 = distribution.get_rate(0.0, 100.0)
        rate2 = distribution.get_rate(30.0, 100.0)
        rate3 = distribution.get_rate(60.0, 100.0)
        assert rate1 == rate2 == rate3 == 100.0


class TestConstantDistributionValidate:
    def test_validate_passes_with_no_rps(self, distribution):
        distribution.initialize({})
        assert distribution.validate() is True

    def test_validate_passes_with_positive_rps(self, distribution):
        distribution.initialize({"rps": 50})
        assert distribution.validate() is True

    def test_validate_passes_with_decimal_positive_rps(self, distribution):
        distribution.initialize({"rps": 0.5})
        assert distribution.validate() is True

    def test_validate_fails_with_negative_rps(self, distribution):
        distribution.initialize({"rps": -1})
        assert distribution.validate() is False

    def test_validate_fails_with_zero_rps(self, distribution):
        distribution.initialize({"rps": 0})
        assert distribution.validate() is False

    def test_validate_fails_with_invalid_rps_string(self, distribution):
        distribution.initialize({"rps": "invalid"})
        assert distribution.validate() is False


class TestConstantDistributionMetadata:
    def test_metadata_has_correct_name(self, distribution):
        assert distribution.metadata["name"] == "constant"

    def test_metadata_has_correct_version(self, distribution):
        assert distribution.metadata["version"] == "1.0.0"

    def test_metadata_has_rps_parameter(self, distribution):
        assert "rps" in distribution.metadata["parameters"]

    def test_rps_parameter_has_correct_type(self, distribution):
        assert distribution.metadata["parameters"]["rps"]["type"] == "float"

    def test_rps_parameter_is_not_required(self, distribution):
        assert distribution.metadata["parameters"]["rps"]["required"] is False

    def test_rps_parameter_has_description(self, distribution):
        desc = distribution.metadata["parameters"]["rps"]["description"]
        assert "requests per second" in desc
