import pytest
from primes.distributions.poisson import PoissonDistribution


@pytest.fixture
def distribution():
    return PoissonDistribution()


class TestPoissonDistributionGetRate:
    def test_rate_varies_around_target(self, distribution):
        """Test that rates vary around the target value using random noise."""
        distribution.initialize({})
        target_rps = 100.0

        # Generate multiple rates and check they vary
        rates = [distribution.get_rate(1.0, target_rps) for _ in range(100)]

        # All rates should be non-negative
        assert all(rate >= 0 for rate in rates), "Rates should never be negative"

        # Average should be close to target (within 20% tolerance for random variation)
        avg_rate = sum(rates) / len(rates)
        assert 80 <= avg_rate <= 120, (
            f"Average rate {avg_rate} should be near target {target_rps}"
        )

    def test_rate_never_negative(self, distribution):
        """Test that rates never go negative even with high noise."""
        distribution.initialize({"variance_scale": 10.0})

        # Generate many rates with high variance
        rates = [distribution.get_rate(1.0, 100) for _ in range(1000)]

        # All rates should be non-negative due to max(0, ...) in get_rate
        assert all(rate >= 0 for rate in rates), "Rates should never go negative"

    def test_rate_with_lambda_param(self, distribution):
        """Test that lambda_param overrides target_rps."""
        distribution.initialize({"lambda_param": 50.0})
        target_rps = 100.0  # Should be ignored

        # Generate rates and check they're around lambda_param
        rates = [distribution.get_rate(1.0, target_rps) for _ in range(100)]

        # Average should be close to lambda_param (not target_rps)
        avg_rate = sum(rates) / len(rates)
        assert 40 <= avg_rate <= 60, (
            f"Average rate {avg_rate} should be near lambda_param 50.0"
        )

    def test_rate_with_variance_scale(self, distribution):
        """Test that variance_scale affects rate variation."""
        # Test with low variance
        distribution.initialize({"variance_scale": 0.1})
        rates_low = [distribution.get_rate(1.0, 100) for _ in range(100)]
        std_low = (
            sum((r - sum(rates_low) / len(rates_low)) ** 2 for r in rates_low)
            / len(rates_low)
        ) ** 0.5

        # Test with high variance
        distribution.initialize({"variance_scale": 2.0})
        rates_high = [distribution.get_rate(1.0, 100) for _ in range(100)]
        std_high = (
            sum((r - sum(rates_high) / len(rates_high)) ** 2 for r in rates_high)
            / len(rates_high)
        ) ** 0.5

        # High variance should have greater standard deviation
        assert std_high > std_low, "Higher variance_scale should produce more variation"


class TestPoissonDistributionValidate:
    def test_validate_passes_with_default_params(self, distribution):
        """Test that validate passes with no parameters."""
        distribution.initialize({})
        assert distribution.validate() is True

    def test_validate_passes_with_positive_lambda_param(self, distribution):
        """Test that validate passes with positive lambda_param."""
        distribution.initialize({"lambda_param": 50.0})
        assert distribution.validate() is True

    def test_validate_passes_with_float_lambda_param(self, distribution):
        """Test that validate passes with float lambda_param."""
        distribution.initialize({"lambda_param": 123.456})
        assert distribution.validate() is True

    def test_validate_passes_with_positive_variance_scale(self, distribution):
        """Test that validate passes with positive variance_scale."""
        distribution.initialize({"variance_scale": 1.5})
        assert distribution.validate() is True

    def test_validate_passes_with_small_positive_variance_scale(self, distribution):
        """Test that validate passes with small positive variance_scale."""
        distribution.initialize({"variance_scale": 0.01})
        assert distribution.validate() is True

    def test_validate_passes_with_both_params_valid(self, distribution):
        """Test that validate passes with both parameters valid."""
        distribution.initialize({"lambda_param": 50.0, "variance_scale": 1.0})
        assert distribution.validate() is True

    def test_validate_fails_with_negative_lambda_param(self, distribution):
        """Test that validate fails with negative lambda_param."""
        distribution.initialize({"lambda_param": -10.0})
        assert distribution.validate() is False

    def test_validate_fails_with_zero_lambda_param(self, distribution):
        """Test that validate fails with zero lambda_param."""
        distribution.initialize({"lambda_param": 0.0})
        assert distribution.validate() is False

    def test_validate_fails_with_zero_variance_scale(self, distribution):
        """Test that validate fails with zero variance_scale."""
        distribution.initialize({"variance_scale": 0.0})
        assert distribution.validate() is False

    def test_validate_fails_with_negative_variance_scale(self, distribution):
        """Test that validate fails with negative variance_scale."""
        distribution.initialize({"variance_scale": -1.0})
        assert distribution.validate() is False

    def test_validate_fails_with_invalid_lambda_param(self, distribution):
        """Test that validate fails with invalid lambda_param input."""
        distribution.initialize({"lambda_param": "invalid"})
        assert distribution.validate() is False

    def test_validate_fails_with_invalid_variance_scale(self, distribution):
        """Test that validate fails with invalid variance_scale input."""
        distribution.initialize({"variance_scale": "invalid"})
        assert distribution.validate() is False

    @pytest.mark.parametrize(
        "lambda_param,variance_scale,expected",
        [
            (None, 1.0, True),  # Default lambda, valid variance
            (50.0, 1.0, True),  # Valid lambda, valid variance
            (0.0, 1.0, False),  # Invalid lambda (zero)
            (-10.0, 1.0, False),  # Invalid lambda (negative)
            (50.0, 0.0, False),  # Valid lambda, invalid variance (zero)
            (50.0, -1.0, False),  # Valid lambda, invalid variance (negative)
        ],
    )
    def test_validate_parameter_combinations(
        self, distribution, lambda_param, variance_scale, expected
    ):
        """Test validate with various parameter combinations."""
        config = {}
        if lambda_param is not None:
            config["lambda_param"] = lambda_param
        config["variance_scale"] = variance_scale

        distribution.initialize(config)
        assert distribution.validate() is expected


class TestPoissonDistributionMetadata:
    def test_metadata_has_correct_name(self, distribution):
        assert distribution.metadata["name"] == "poisson"

    def test_metadata_has_correct_version(self, distribution):
        assert distribution.metadata["version"] == "1.0.0"

    def test_metadata_has_lambda_param_parameter(self, distribution):
        assert "lambda_param" in distribution.metadata["parameters"]

    def test_lambda_param_parameter_has_correct_type(self, distribution):
        assert distribution.metadata["parameters"]["lambda_param"]["type"] == "float"

    def test_lambda_param_parameter_is_not_required(self, distribution):
        assert distribution.metadata["parameters"]["lambda_param"]["required"] is False

    def test_lambda_param_parameter_has_default_value(self, distribution):
        assert distribution.metadata["parameters"]["lambda_param"]["default"] is None

    def test_lambda_param_parameter_has_description(self, distribution):
        desc = distribution.metadata["parameters"]["lambda_param"]["description"]
        assert "average" in desc.lower()
        assert "requests" in desc.lower()

    def test_metadata_has_variance_scale_parameter(self, distribution):
        assert "variance_scale" in distribution.metadata["parameters"]

    def test_variance_scale_parameter_has_correct_type(self, distribution):
        assert distribution.metadata["parameters"]["variance_scale"]["type"] == "float"

    def test_variance_scale_parameter_is_not_required(self, distribution):
        assert (
            distribution.metadata["parameters"]["variance_scale"]["required"] is False
        )

    def test_variance_scale_parameter_has_default_value(self, distribution):
        assert distribution.metadata["parameters"]["variance_scale"]["default"] == 1.0

    def test_variance_scale_parameter_has_description(self, distribution):
        desc = distribution.metadata["parameters"]["variance_scale"]["description"]
        assert "variance" in desc.lower()


class TestPoissonDistributionInitialize:
    def test_initialize_with_default_config(self, distribution):
        distribution.initialize({})
        assert distribution.lambda_param is None
        assert distribution.variance_scale == 1.0

    def test_initialize_with_lambda_param(self, distribution):
        distribution.initialize({"lambda_param": 50.0})
        assert distribution.lambda_param == 50.0
        assert distribution.variance_scale == 1.0

    def test_initialize_with_variance_scale(self, distribution):
        distribution.initialize({"variance_scale": 0.5})
        assert distribution.lambda_param is None
        assert distribution.variance_scale == 0.5

    def test_initialize_with_both_params(self, distribution):
        distribution.initialize({"lambda_param": 100.0, "variance_scale": 2.0})
        assert distribution.lambda_param == 100.0
        assert distribution.variance_scale == 2.0

    def test_initialize_with_int_lambda_param(self, distribution):
        distribution.initialize({"lambda_param": 75})
        assert distribution.lambda_param == 75.0

    def test_initialize_with_string_variance_scale(self, distribution):
        distribution.initialize({"variance_scale": "1.5"})
        assert distribution.variance_scale == 1.5

    def test_initialize_stores_config(self, distribution):
        config = {"lambda_param": 50.0, "variance_scale": 1.0, "custom": "value"}
        distribution.initialize(config)
        assert distribution.config == config
