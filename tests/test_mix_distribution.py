import pytest

from primes.distributions.mix import MixDistribution


@pytest.fixture
def distribution():
    return MixDistribution()


class TestMixDistributionGetRate:
    def test_returns_weighted_sum_with_normalized_weights(self, distribution):
        distribution.initialize(
            {
                "components": [
                    {
                        "weight": 2.0,
                        "distribution": {"name": "constant", "config": {"rps": 30}},
                    },
                    {
                        "weight": 1.0,
                        "distribution": {"name": "constant", "config": {"rps": 60}},
                    },
                ]
            }
        )
        rate = distribution.get_rate(5.0, 100.0)
        assert rate == 40.0

    def test_mix_target_rps_applies_to_components(self, distribution):
        distribution.initialize(
            {
                "target_rps": 120,
                "components": [
                    {
                        "weight": 1.0,
                        "distribution": {"name": "constant", "config": {}},
                    }
                ],
            }
        )
        rate = distribution.get_rate(1.0, 50.0)
        assert rate == 120.0

    def test_component_target_rps_overrides_mix_target(self, distribution):
        distribution.initialize(
            {
                "target_rps": 120,
                "components": [
                    {
                        "weight": 1.0,
                        "distribution": {
                            "name": "constant",
                            "config": {"target_rps": 30},
                        },
                    }
                ],
            }
        )
        rate = distribution.get_rate(1.0, 50.0)
        assert rate == 30.0


class TestMixDistributionValidate:
    def test_validate_passes_with_valid_components(self, distribution):
        distribution.initialize(
            {
                "components": [
                    {
                        "weight": 1.0,
                        "distribution": {"name": "constant", "config": {}},
                    }
                ]
            }
        )
        assert distribution.validate() is True

    def test_validate_fails_with_missing_components(self, distribution):
        distribution.initialize({})
        assert distribution.validate() is False

    def test_validate_fails_with_non_positive_weight(self, distribution):
        distribution.initialize(
            {
                "components": [
                    {
                        "weight": 0.0,
                        "distribution": {"name": "constant", "config": {}},
                    }
                ]
            }
        )
        assert distribution.validate() is False


class TestMixDistributionMetadata:
    def test_metadata_has_correct_name(self, distribution):
        assert distribution.metadata["name"] == "mix"
