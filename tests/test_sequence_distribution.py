import pytest

from primes.distributions.sequence import SequenceDistribution


@pytest.fixture
def distribution():
    return SequenceDistribution()


class TestSequenceDistributionGetRate:
    def test_stage_selection_by_elapsed_time(self, distribution):
        distribution.initialize(
            {
                "stages": [
                    {
                        "duration_seconds": 10,
                        "distribution": {"name": "constant", "config": {"rps": 10}},
                    },
                    {
                        "duration_seconds": 10,
                        "distribution": {"name": "constant", "config": {"rps": 20}},
                    },
                ],
                "post_behavior": "hold_last",
            }
        )
        assert distribution.get_rate(5.0, 100.0) == 10.0
        assert distribution.get_rate(15.0, 100.0) == 20.0

    def test_stage_elapsed_time_resets_per_stage(self, distribution):
        distribution.initialize(
            {
                "stages": [
                    {
                        "duration_seconds": 10,
                        "distribution": {
                            "name": "linear",
                            "config": {"ramp_duration": 10},
                        },
                    },
                    {
                        "duration_seconds": 10,
                        "distribution": {
                            "name": "linear",
                            "config": {"ramp_duration": 10},
                        },
                    },
                ],
                "post_behavior": "hold_last",
            }
        )
        assert distribution.get_rate(12.0, 100.0) == 20.0

    def test_post_behavior_zero(self, distribution):
        distribution.initialize(
            {
                "stages": [
                    {
                        "duration_seconds": 5,
                        "distribution": {"name": "constant", "config": {"rps": 10}},
                    }
                ],
                "post_behavior": "zero",
            }
        )
        assert distribution.get_rate(6.0, 100.0) == 0.0

    def test_post_behavior_repeat(self, distribution):
        distribution.initialize(
            {
                "stages": [
                    {
                        "duration_seconds": 10,
                        "distribution": {
                            "name": "linear",
                            "config": {"ramp_duration": 10},
                        },
                    },
                    {
                        "duration_seconds": 10,
                        "distribution": {
                            "name": "constant",
                            "config": {"rps": 50},
                        },
                    },
                ],
                "post_behavior": "repeat",
            }
        )
        assert distribution.get_rate(22.0, 100.0) == 20.0


class TestSequenceDistributionValidate:
    def test_validate_passes_with_valid_stages(self, distribution):
        distribution.initialize(
            {
                "stages": [
                    {
                        "duration_seconds": 5,
                        "distribution": {"name": "constant", "config": {}},
                    }
                ],
                "post_behavior": "hold_last",
            }
        )
        assert distribution.validate() is True

    def test_validate_fails_with_missing_stages(self, distribution):
        distribution.initialize({})
        assert distribution.validate() is False

    def test_validate_fails_with_non_positive_duration(self, distribution):
        distribution.initialize(
            {
                "stages": [
                    {
                        "duration_seconds": 0,
                        "distribution": {"name": "constant", "config": {}},
                    }
                ]
            }
        )
        assert distribution.validate() is False


class TestSequenceDistributionMetadata:
    def test_metadata_has_correct_name(self, distribution):
        assert distribution.metadata["name"] == "sequence"
