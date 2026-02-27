"""
Tests for the test utilities module (meta-testing!).
"""

from tests.distribution_test_utils import (
    DistributionMetadataTests,
)
from primes.distributions.constant import ConstantDistribution
from primes.distributions.linear import LinearDistribution


class TestDistributionFixture:
    def test_fixture_creates_distribution_instance(self):
        # Direct instantiation test
        dist = ConstantDistribution()
        assert isinstance(dist, ConstantDistribution)

    def test_fixture_distribution_can_be_initialized(self):
        dist = ConstantDistribution()
        dist.initialize({})
        assert hasattr(dist, "config")


class TestDistributionMetadataTests:
    def test_has_correct_name(self):
        dist = ConstantDistribution()
        DistributionMetadataTests.test_has_correct_name(dist, "constant")

    def test_has_correct_version(self):
        dist = ConstantDistribution()
        DistributionMetadataTests.test_has_correct_version(dist, "1.0.0")

    def test_has_correct_version_custom(self):
        dist = LinearDistribution()
        DistributionMetadataTests.test_has_correct_version(dist, "1.0.0")

    def test_parameter_exists(self):
        dist = ConstantDistribution()
        DistributionMetadataTests.test_parameter_exists(dist, "rps")

    def test_parameter_has_type(self):
        dist = ConstantDistribution()
        DistributionMetadataTests.test_parameter_has_type(dist, "rps", "float")

    def test_parameter_has_description(self):
        dist = ConstantDistribution()
        assert (
            "requests per second"
            in DistributionMetadataTests._get_parameter_description(dist, "rps").lower()
        )
