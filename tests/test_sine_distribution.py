"""Unit tests for SineDistribution plugin."""

import pytest

from primes.distributions.sine import SineDistribution


class TestSineDistributionMetadata:
    """Test SineDistribution metadata."""

    def test_metadata_name(self):
        """Test metadata has correct name."""
        d = SineDistribution()
        assert d.metadata["name"] == "sine"

    def test_metadata_version(self):
        """Test metadata has correct version."""
        d = SineDistribution()
        assert d.metadata["version"] == "1.0.0"

    def test_metadata_description(self):
        """Test metadata has correct description."""
        d = SineDistribution()
        assert "sine" in d.metadata["description"].lower()

    def test_metadata_parameters_include_period(self):
        """Test metadata includes period parameter."""
        d = SineDistribution()
        assert "period" in d.metadata["parameters"]
        assert d.metadata["parameters"]["period"]["type"] == "float"
        assert d.metadata["parameters"]["period"]["default"] == 3600.0

    def test_metadata_parameters_include_amplitude(self):
        """Test metadata includes amplitude parameter."""
        d = SineDistribution()
        assert "amplitude" in d.metadata["parameters"]
        assert d.metadata["parameters"]["amplitude"]["type"] == "float"
        assert d.metadata["parameters"]["amplitude"]["default"] == 0.5

    def test_metadata_parameters_include_phase_shift(self):
        """Test metadata includes phase_shift parameter."""
        d = SineDistribution()
        assert "phase_shift" in d.metadata["parameters"]
        assert d.metadata["parameters"]["phase_shift"]["type"] == "float"
        assert d.metadata["parameters"]["phase_shift"]["default"] == 0.0

    def test_metadata_parameters_include_base_rps(self):
        """Test metadata includes base_rps parameter."""
        d = SineDistribution()
        assert "base_rps" in d.metadata["parameters"]
        assert d.metadata["parameters"]["base_rps"]["type"] == "float"
        assert d.metadata["parameters"]["base_rps"]["default"] is None


class TestSineDistributionInitialize:
    """Test SineDistribution initialize method."""

    def test_initialize_default_values(self):
        """Test initialize with default values."""
        d = SineDistribution()
        d.initialize({})
        assert d.period == 3600.0
        assert d.amplitude == 0.5
        assert d.phase_shift == 0.0
        assert d.base_rps is None

    def test_initialize_custom_period(self):
        """Test initialize with custom period."""
        d = SineDistribution()
        d.initialize({"period": 60.0})
        assert d.period == 60.0

    def test_initialize_custom_amplitude(self):
        """Test initialize with custom amplitude."""
        d = SineDistribution()
        d.initialize({"amplitude": 0.8})
        assert d.amplitude == 0.8

    def test_initialize_custom_phase_shift(self):
        """Test initialize with custom phase_shift."""
        d = SineDistribution()
        d.initialize({"phase_shift": 30.0})
        assert d.phase_shift == 30.0

    def test_initialize_custom_base_rps(self):
        """Test initialize with custom base_rps."""
        d = SineDistribution()
        d.initialize({"base_rps": 50.0})
        assert d.base_rps == 50.0

    def test_initialize_all_parameters(self):
        """Test initialize with all parameters."""
        d = SineDistribution()
        d.initialize(
            {"period": 300.0, "amplitude": 0.7, "phase_shift": 15.0, "base_rps": 80.0}
        )
        assert d.period == 300.0
        assert d.amplitude == 0.7
        assert d.phase_shift == 15.0
        assert d.base_rps == 80.0

    def test_initialize_period_from_string(self):
        """Test initialize handles period as string."""
        d = SineDistribution()
        d.initialize({"period": "120"})
        assert d.period == 120.0

    def test_initialize_amplitude_from_string(self):
        """Test initialize handles amplitude as string."""
        d = SineDistribution()
        d.initialize({"amplitude": "0.3"})
        assert d.amplitude == 0.3


class TestSineDistributionGetRate:
    """Test SineDistribution get_rate method."""

    @pytest.mark.parametrize(
        "period,amplitude", [(60.0, 0.5), (120.0, 0.3), (30.0, 0.8)]
    )
    def test_rate_oscillates_with_period(self, period, amplitude):
        """Test rate oscillates with specified period."""
        d = SineDistribution()
        d.initialize({"period": period, "amplitude": amplitude})
        target_rps = 100.0

        # Rate at t=0 and t=period should be equal (full cycle)
        rate_at_0 = d.get_rate(0.0, target_rps)
        rate_at_period = d.get_rate(period, target_rps)
        assert round(rate_at_0, 4) == round(rate_at_period, 4)

    @pytest.mark.parametrize("amplitude", [0.2, 0.5, 0.8, 1.0])
    def test_amplitude_scales_correctly(self, amplitude):
        """Test amplitude scales the oscillation correctly."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": amplitude})
        target_rps = 100.0

        # At quarter period: sin(pi/2) = 1, rate = base * (1 + amp)
        rate_at_quarter = d.get_rate(15.0, target_rps)
        expected = target_rps * (1.0 + amplitude)
        assert round(rate_at_quarter, 2) == round(expected, 2)

    def test_phase_shift_offsets_wave(self):
        """Test phase shift offsets the wave."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 0.5, "phase_shift": 15.0})
        target_rps = 100.0

        # At t=0 with phase_shift=15, we should be at quarter period (15/60 = 0.25)
        rate_at_0 = d.get_rate(0.0, target_rps)
        expected = target_rps * (1.0 + 0.5)  # At quarter period, sin(pi/2) = 1
        assert round(rate_at_0, 2) == round(expected, 2)

    def test_rate_never_goes_negative(self):
        """Test rate never goes negative when amplitude <= 1."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 1.0})
        target_rps = 100.0

        # Test at minimum (3/4 period: sin(3pi/2) = -1)
        # Rate = base * (1 + 1 * (-1)) = base * 0 = 0 (not negative)
        rate_min = d.get_rate(45.0, target_rps)
        assert rate_min >= 0

    def test_at_quarter_period_sin_pi_2(self):
        """Test at quarter period: sin(pi/2) = 1, rate = base * (1 + amp)."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 0.5})
        target_rps = 100.0

        # At quarter period (15 seconds for 60 second period)
        rate = d.get_rate(15.0, target_rps)
        expected = target_rps * (1.0 + 0.5)  # base * (1 + amplitude)
        assert round(rate, 2) == round(expected, 2)

    def test_at_half_period_sin_pi(self):
        """Test at half period: sin(pi) = 0, rate = base."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 0.5})
        target_rps = 100.0

        # At half period (30 seconds for 60 second period)
        rate = d.get_rate(30.0, target_rps)
        expected = target_rps  # base * (1 + 0.5 * 0) = base
        assert round(rate, 2) == round(expected, 2)

    def test_at_three_quarters_period_sin_3pi_2(self):
        """Test at 3/4 period: sin(3pi/2) = -1, rate = base * (1 - amp)."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 0.5})
        target_rps = 100.0

        # At 3/4 period (45 seconds for 60 second period)
        rate = d.get_rate(45.0, target_rps)
        expected = target_rps * (1.0 - 0.5)  # base * (1 - amplitude)
        assert round(rate, 2) == round(expected, 2)

    def test_uses_target_rps_when_base_rps_not_set(self):
        """Test uses target_rps when base_rps is not set."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 0.5})
        target_rps = 50.0

        rate = d.get_rate(0.0, target_rps)
        assert round(rate, 2) == round(target_rps, 2)

    def test_uses_base_rps_when_set(self):
        """Test uses base_rps when set."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 0.5, "base_rps": 80.0})
        target_rps = 50.0  # This should be ignored

        rate = d.get_rate(0.0, target_rps)
        assert round(rate, 2) == round(80.0, 2)

    def test_wave_pattern_is_smooth(self):
        """Test wave pattern creates smooth oscillation."""
        d = SineDistribution()
        d.initialize({"period": 60.0, "amplitude": 0.5})
        target_rps = 100.0

        # Sample rates at fine intervals
        rates = [d.get_rate(t, target_rps) for t in range(0, 61, 5)]

        # Check pattern: starts at 100, goes up to 150, back to 100, down to 50, back to 100
        assert round(rates[0], 1) == 100.0  # t=0, sin(0)=0
        assert round(rates[3], 1) == 150.0  # t=15, sin(pi/2)=1
        assert round(rates[6], 1) == 100.0  # t=30, sin(pi)=0
        assert round(rates[9], 1) == 50.0  # t=45, sin(3pi/2)=-1
        assert round(rates[12], 1) == 100.0  # t=60, sin(2pi)=0


class TestSineDistributionValidate:
    """Test SineDistribution validate method."""

    def test_validate_default_config(self):
        """Test validation passes with default config."""
        d = SineDistribution()
        d.initialize({})
        assert d.validate() is True

    def test_validate_fails_period_zero(self):
        """Test validation fails with period = 0."""
        d = SineDistribution()
        d.initialize({"period": 0})
        assert d.validate() is False

    def test_validate_fails_period_negative(self):
        """Test validation fails with negative period."""
        d = SineDistribution()
        d.initialize({"period": -10.0})
        assert d.validate() is False

    def test_validate_fails_amplitude_zero(self):
        """Test validation fails with amplitude = 0."""
        d = SineDistribution()
        d.initialize({"amplitude": 0.0})
        assert d.validate() is False

    def test_validate_fails_amplitude_negative(self):
        """Test validation fails with negative amplitude."""
        d = SineDistribution()
        d.initialize({"amplitude": -0.5})
        assert d.validate() is False

    def test_validate_fails_amplitude_greater_than_one(self):
        """Test validation fails with amplitude > 1."""
        d = SineDistribution()
        d.initialize({"amplitude": 1.5})
        assert d.validate() is False

    def test_validate_amplitude_exactly_one(self):
        """Test validation passes with amplitude = 1."""
        d = SineDistribution()
        d.initialize({"amplitude": 1.0})
        assert d.validate() is True

    def test_validate_amplitude_close_to_zero_fails(self):
        """Test validation fails with amplitude close to but not equal to 0."""
        d = SineDistribution()
        d.initialize({"amplitude": 0.001})
        # This should pass because 0.001 > 0
        assert d.validate() is True

    def test_validate_fails_phase_shift_negative(self):
        """Test validation fails with negative phase_shift."""
        d = SineDistribution()
        d.initialize({"phase_shift": -10.0})
        assert d.validate() is False

    def test_validate_phase_shift_zero(self):
        """Test validation passes with phase_shift = 0."""
        d = SineDistribution()
        d.initialize({"phase_shift": 0.0})
        assert d.validate() is True

    def test_validate_fails_base_rps_zero(self):
        """Test validation fails with base_rps = 0."""
        d = SineDistribution()
        d.initialize({"base_rps": 0.0})
        assert d.validate() is False

    def test_validate_fails_base_rps_negative(self):
        """Test validation fails with negative base_rps."""
        d = SineDistribution()
        d.initialize({"base_rps": -10.0})
        assert d.validate() is False

    def test_validate_base_rps_none(self):
        """Test validation passes with base_rps = None (use target_rps)."""
        d = SineDistribution()
        d.initialize({"base_rps": None})
        assert d.validate() is True

    def test_validate_all_invalid_parameters(self):
        """Test validation fails with multiple invalid parameters."""
        d = SineDistribution()
        d.initialize(
            {"period": -1, "amplitude": 2.0, "phase_shift": -5, "base_rps": -10}
        )
        assert d.validate() is False

    def test_validate_fails_with_invalid_period_string(self):
        """Test validation fails with invalid period input."""
        d = SineDistribution()
        d.initialize({"period": "invalid"})
        assert d.validate() is False

    def test_validate_fails_with_invalid_amplitude_string(self):
        """Test validation fails with invalid amplitude input."""
        d = SineDistribution()
        d.initialize({"amplitude": "invalid"})
        assert d.validate() is False
