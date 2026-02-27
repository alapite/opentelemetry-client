import pytest
from primes.distributions.linear import LinearDistribution


@pytest.fixture
def distribution():
    return LinearDistribution()


class TestLinearDistributionGetRate:
    @pytest.mark.parametrize(
        "time_elapsed,ramp_duration,target_rps,expected_rate",
        [
            (0.0, 10.0, 100.0, 0.0),  # At t=0, rate is 0
            (5.0, 10.0, 100.0, 50.0),  # At half ramp, rate is half target
            (2.5, 10.0, 100.0, 25.0),  # At quarter ramp, rate is quarter target
            (10.0, 10.0, 100.0, 100.0),  # At ramp end, rate equals target
            (20.0, 10.0, 100.0, 100.0),  # After ramp, rate stays at target
            (15.0, 30.0, 200.0, 100.0),  # Half ramp with different values
        ],
    )
    def test_get_rate_linear_interpolation(
        self, distribution, time_elapsed, ramp_duration, target_rps, expected_rate
    ):
        distribution.initialize({"ramp_duration": ramp_duration})
        rate = distribution.get_rate(time_elapsed, target_rps)
        assert rate == expected_rate

    def test_get_rate_zero_at_start(self, distribution):
        distribution.initialize({"ramp_duration": 30.0})
        rate = distribution.get_rate(0.0, 100.0)
        assert rate == 0.0

    def test_get_rate_reaches_target_at_ramp_end(self, distribution):
        distribution.initialize({"ramp_duration": 20.0})
        rate = distribution.get_rate(20.0, 50.0)
        assert rate == 50.0

    def test_get_rate_stays_constant_after_ramp(self, distribution):
        distribution.initialize({"ramp_duration": 10.0})
        rate1 = distribution.get_rate(10.0, 100.0)
        rate2 = distribution.get_rate(20.0, 100.0)
        rate3 = distribution.get_rate(100.0, 100.0)
        assert rate1 == rate2 == rate3 == 100.0

    def test_get_rate_with_custom_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": 5.0})
        rate = distribution.get_rate(2.5, 200.0)
        assert rate == 100.0  # Half of target at half ramp


class TestLinearDistributionValidate:
    def test_validate_passes_with_default_ramp_duration(self, distribution):
        distribution.initialize({})
        assert distribution.validate() is True

    def test_validate_passes_with_positive_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": 60.0})
        assert distribution.validate() is True

    def test_validate_passes_with_small_positive_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": 0.1})
        assert distribution.validate() is True

    def test_validate_fails_with_zero_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": 0.0})
        assert distribution.validate() is False

    def test_validate_fails_with_negative_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": -1.0})
        assert distribution.validate() is False

    def test_validate_fails_with_invalid_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": "invalid"})
        assert distribution.validate() is False


class TestLinearDistributionMetadata:
    def test_metadata_has_correct_name(self, distribution):
        assert distribution.metadata["name"] == "linear"

    def test_metadata_has_correct_version(self, distribution):
        assert distribution.metadata["version"] == "1.0.0"

    def test_metadata_has_ramp_duration_parameter(self, distribution):
        assert "ramp_duration" in distribution.metadata["parameters"]

    def test_ramp_duration_parameter_has_correct_type(self, distribution):
        assert distribution.metadata["parameters"]["ramp_duration"]["type"] == "float"

    def test_ramp_duration_parameter_is_not_required(self, distribution):
        assert distribution.metadata["parameters"]["ramp_duration"]["required"] is False

    def test_ramp_duration_parameter_has_default_value(self, distribution):
        assert distribution.metadata["parameters"]["ramp_duration"]["default"] == 60.0

    def test_ramp_duration_parameter_has_description(self, distribution):
        desc = distribution.metadata["parameters"]["ramp_duration"]["description"]
        assert "ramp" in desc.lower()
        assert "duration" in desc.lower()


class TestLinearDistributionInitialize:
    def test_initialize_with_default_config(self, distribution):
        distribution.initialize({})
        assert distribution.ramp_duration == 60.0

    def test_initialize_with_custom_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": 30.0})
        assert distribution.ramp_duration == 30.0

    def test_initialize_with_int_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": 45})
        assert distribution.ramp_duration == 45.0

    def test_initialize_with_string_ramp_duration(self, distribution):
        distribution.initialize({"ramp_duration": "25.5"})
        assert distribution.ramp_duration == 25.5

    def test_initialize_stores_config(self, distribution):
        config = {"ramp_duration": 20.0, "custom": "value"}
        distribution.initialize(config)
        assert distribution.config == config
