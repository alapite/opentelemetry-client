import pytest
from primes.distributions.step import StepDistribution


@pytest.fixture
def distribution():
    return StepDistribution()


class TestStepDistributionGetRate:
    def test_rate_before_first_step_returns_default_rps(self, distribution):
        """Test that rate before first step returns default_rps."""
        distribution.initialize({"steps": [[10, 50], [30, 100]], "default_rps": 10})
        assert distribution.get_rate(5, 100) == 10

    def test_rate_at_step_time_returns_step_rate(self, distribution):
        """Test that rate at step time returns step rate."""
        distribution.initialize({"steps": [[10, 50], [30, 100]], "default_rps": 10})
        assert distribution.get_rate(10, 100) == 50
        assert distribution.get_rate(30, 100) == 100

    def test_rate_after_step_returns_last_step_rate(self, distribution):
        """Test that rate after step returns last step rate."""
        distribution.initialize({"steps": [[10, 50], [30, 100]], "default_rps": 10})
        assert distribution.get_rate(20, 100) == 50
        assert distribution.get_rate(60, 100) == 100

    def test_multiple_steps_in_order(self, distribution):
        """Test multiple steps are applied in correct order."""
        distribution.initialize(
            {"steps": [[10, 25], [20, 50], [30, 75], [40, 100]], "default_rps": 5}
        )
        assert distribution.get_rate(5, 200) == 5  # Before first step
        assert distribution.get_rate(10, 200) == 25  # First step
        assert distribution.get_rate(15, 200) == 25  # Between first and second
        assert distribution.get_rate(20, 200) == 50  # Second step
        assert distribution.get_rate(25, 200) == 50  # Between second and third
        assert distribution.get_rate(30, 200) == 75  # Third step
        assert distribution.get_rate(35, 200) == 75  # Between third and fourth
        assert distribution.get_rate(40, 200) == 100  # Fourth step
        assert distribution.get_rate(50, 200) == 100  # After fourth step

    def test_no_steps_returns_target_rps(self, distribution):
        """Test that with no steps, returns target_rps."""
        distribution.initialize({})
        assert distribution.get_rate(10, 100) == 100
        assert distribution.get_rate(50, 200) == 200

    def test_steps_sorted_automatically(self, distribution):
        """Test that steps are sorted automatically regardless of input order."""
        # Provide steps in reverse order
        distribution.initialize(
            {"steps": [[40, 100], [10, 25], [30, 75], [20, 50]], "default_rps": 5}
        )
        # Should still apply in time order
        assert distribution.get_rate(5, 200) == 5
        assert distribution.get_rate(15, 200) == 25
        assert distribution.get_rate(25, 200) == 50
        assert distribution.get_rate(35, 200) == 75
        assert distribution.get_rate(45, 200) == 100

    def test_json_string_format(self, distribution):
        """Test that steps can be provided as JSON string."""
        distribution.initialize({"steps": "[[10, 50], [30, 100]]", "default_rps": 10})
        assert distribution.get_rate(5, 100) == 10
        assert distribution.get_rate(20, 100) == 50
        assert distribution.get_rate(40, 100) == 100

    def test_float_times_and_rates(self, distribution):
        """Test that float times and rates work correctly."""
        distribution.initialize(
            {"steps": [[10.5, 50.5], [30.7, 100.3]], "default_rps": 5.5}
        )
        assert distribution.get_rate(10, 100) == 5.5
        assert distribution.get_rate(10.5, 100) == 50.5
        assert distribution.get_rate(30.7, 100) == 100.3

    @pytest.mark.parametrize(
        "time_elapsed,expected",
        [
            (0, 10),  # Exactly at start
            (5, 10),  # Before first step
            (10, 50),  # At first step
            (25, 50),  # Between steps
            (30, 100),  # At second step
            (100, 100),  # After all steps
        ],
    )
    def test_rate_at_specific_times(self, distribution, time_elapsed, expected):
        """Test rate at specific time points."""
        distribution.initialize({"steps": [[10, 50], [30, 100]], "default_rps": 10})
        assert distribution.get_rate(time_elapsed, 100) == expected


class TestStepDistributionValidate:
    def test_validate_passes_with_valid_config(self, distribution):
        """Test that validate passes with valid configuration."""
        distribution.initialize({"steps": [[10, 50], [30, 100]], "default_rps": 10})
        assert distribution.validate() is True

    def test_validate_passes_with_no_steps(self, distribution):
        """Test that validate passes with no steps."""
        distribution.initialize({"default_rps": 10})
        assert distribution.validate() is True

    def test_validate_passes_with_empty_config(self, distribution):
        """Test that validate passes with empty config."""
        distribution.initialize({})
        assert distribution.validate() is True

    def test_validate_passes_with_zero_time(self, distribution):
        """Test that validate passes with zero time (not negative)."""
        distribution.initialize({"steps": [[0, 50]], "default_rps": 10})
        assert distribution.validate() is True

    def test_validate_passes_with_zero_rate(self, distribution):
        """Test that validate passes with zero rate (not negative)."""
        distribution.initialize({"steps": [[10, 0]], "default_rps": 0})
        assert distribution.validate() is True

    def test_validate_passes_with_zero_default_rps(self, distribution):
        """Test that validate passes with zero default_rps."""
        distribution.initialize({"steps": [[10, 50]], "default_rps": 0})
        assert distribution.validate() is True

    def test_validate_fails_with_negative_time(self, distribution):
        """Test that validate fails with negative time."""
        distribution.initialize({"steps": [[-1, 50]], "default_rps": 10})
        assert distribution.validate() is False

    def test_validate_fails_with_negative_rate(self, distribution):
        """Test that validate fails with negative rate."""
        distribution.initialize({"steps": [[10, -50]], "default_rps": 10})
        assert distribution.validate() is False

    def test_validate_fails_with_negative_default_rps(self, distribution):
        """Test that validate fails with negative default_rps."""
        distribution.initialize({"steps": [[10, 50]], "default_rps": -10})
        assert distribution.validate() is False

    def test_validate_fails_with_invalid_default_rps(self, distribution):
        """Test that validate fails with invalid default_rps input."""
        distribution.initialize({"default_rps": "invalid"})
        assert distribution.validate() is False

    def test_validate_fails_with_malformed_steps(self, distribution):
        """Test that validate fails with malformed steps (not [time, rps] pairs)."""
        distribution.initialize({"steps": [[10]], "default_rps": 10})
        assert distribution.validate() is False

    def test_validate_fails_with_triple_values(self, distribution):
        """Test that validate fails with step having more than 2 values."""
        distribution.initialize({"steps": [[10, 50, 100]], "default_rps": 10})
        assert distribution.validate() is False

    @pytest.mark.parametrize(
        "steps,default_rps,expected",
        [
            ([], 0, True),  # No steps, zero default
            ([[10, 50]], 0, True),  # Valid step
            ([[10, 50], [30, 100]], 0, True),  # Multiple valid steps
            ([[0, 0]], 0, True),  # Zero values
            ([[-1, 50]], 0, False),  # Negative time
            ([[10, -50]], 0, False),  # Negative rate
            ([], -1, False),  # Negative default
            ([[10]], 0, False),  # Malformed step
            ([[10, 50, 100]], 0, False),  # Extra values
        ],
    )
    def test_validate_step_configurations(
        self, distribution, steps, default_rps, expected
    ):
        """Test validate with various step configurations."""
        config = {"steps": steps, "default_rps": default_rps}
        distribution.initialize(config)
        assert distribution.validate() is expected


class TestStepDistributionMetadata:
    def test_metadata_has_correct_name(self, distribution):
        assert distribution.metadata["name"] == "step"

    def test_metadata_has_correct_version(self, distribution):
        assert distribution.metadata["version"] == "1.0.0"

    def test_metadata_has_steps_parameter(self, distribution):
        assert "steps" in distribution.metadata["parameters"]

    def test_steps_parameter_has_correct_type(self, distribution):
        assert distribution.metadata["parameters"]["steps"]["type"] == "str"

    def test_steps_parameter_is_not_required(self, distribution):
        assert distribution.metadata["parameters"]["steps"]["required"] is False

    def test_steps_parameter_has_default_value(self, distribution):
        assert distribution.metadata["parameters"]["steps"]["default"] is None

    def test_steps_parameter_has_description(self, distribution):
        desc = distribution.metadata["parameters"]["steps"]["description"]
        assert "json" in desc.lower()
        assert "time" in desc.lower()
        assert "rps" in desc.lower()

    def test_metadata_has_default_rps_parameter(self, distribution):
        assert "default_rps" in distribution.metadata["parameters"]

    def test_default_rps_parameter_has_correct_type(self, distribution):
        assert distribution.metadata["parameters"]["default_rps"]["type"] == "float"

    def test_default_rps_parameter_is_not_required(self, distribution):
        assert distribution.metadata["parameters"]["default_rps"]["required"] is False

    def test_default_rps_parameter_has_default_value(self, distribution):
        assert distribution.metadata["parameters"]["default_rps"]["default"] == 0.0

    def test_default_rps_parameter_has_description(self, distribution):
        desc = distribution.metadata["parameters"]["default_rps"]["description"]
        assert "rate" in desc.lower()
        assert "first step" in desc.lower()


class TestStepDistributionInitialize:
    def test_initialize_with_default_config(self, distribution):
        distribution.initialize({})
        assert distribution.default_rps == 0.0
        assert distribution.steps == []

    def test_initialize_with_steps_list(self, distribution):
        distribution.initialize({"steps": [[10, 50], [30, 100]], "default_rps": 10})
        assert distribution.default_rps == 10
        assert distribution.steps == [(10.0, 50.0), (30.0, 100.0)]

    def test_initialize_with_steps_json_string(self, distribution):
        distribution.initialize({"steps": "[[10, 50], [30, 100]]", "default_rps": 10})
        assert distribution.default_rps == 10
        assert distribution.steps == [(10.0, 50.0), (30.0, 100.0)]

    def test_initialize_sorts_steps(self, distribution):
        # Input in reverse order
        distribution.initialize({"steps": [[30, 100], [10, 50]], "default_rps": 10})
        assert distribution.steps == [(10.0, 50.0), (30.0, 100.0)]

    def test_initialize_with_float_default_rps(self, distribution):
        distribution.initialize({"default_rps": 12.5})
        assert distribution.default_rps == 12.5

    def test_initialize_with_int_default_rps(self, distribution):
        distribution.initialize({"default_rps": 10})
        assert distribution.default_rps == 10.0

    def test_initialize_with_string_default_rps(self, distribution):
        distribution.initialize({"default_rps": "15.5"})
        assert distribution.default_rps == 15.5

    def test_initialize_converts_step_values_to_float(self, distribution):
        distribution.initialize({"steps": [[10, 50]]})
        assert isinstance(distribution.steps[0][0], float)
        assert isinstance(distribution.steps[0][1], float)
        assert distribution.steps[0][0] == 10.0
        assert distribution.steps[0][1] == 50.0

    def test_initialize_stores_config(self, distribution):
        config = {"steps": [[10, 50]], "default_rps": 10, "custom": "value"}
        distribution.initialize(config)
        assert distribution.config == config

    def test_initialize_handles_malformed_steps_gracefully(self, distribution):
        """Test that initialize handles malformed steps without crashing."""
        # Should not raise exception, just set empty steps
        distribution.initialize({"steps": [[10]], "default_rps": 10})
        assert distribution.steps == []
        assert distribution._parse_error is True
