"""
Reusable test utilities for distribution plugin tests.

This module provides common test patterns and fixture factories used
across multiple distribution test files to reduce duplication.
"""

from typing import Type, Callable
import pytest
from primes.distributions.base import DistributionPlugin


def distribution_fixture(distribution_class: Type[DistributionPlugin]) -> Callable:
    """
    Factory function to create pytest fixtures for distributions.

    Returns a fixture function that creates instances of the specified
    distribution class. Use this to avoid duplicating fixture code.

    Args:
        distribution_class: The distribution plugin class to create fixtures for

    Returns:
        A pytest fixture function

    Examples:
        >>> # In your test file:
        >>> from tests.distribution_test_utils import distribution_fixture
        >>> distribution = distribution_fixture(ConstantDistribution)
        >>>
        >>> # Then use in tests:
        >>> def test_something(distribution):
        >>>     assert distribution.metadata["name"] == "constant"

    Note:
        The fixture function should be assigned to a variable named
        after the distribution (e.g., 'distribution', 'linear_dist', etc.)
    """

    @pytest.fixture
    def fixture():
        return distribution_class()

    return fixture


class DistributionMetadataTests:
    """
    Reusable test class for metadata validation.

    Provides static helper methods for testing distribution metadata.
    Subclass or use directly in your test classes.

    Examples:
        >>> class TestConstantDistributionMetadata(DistributionMetadataTests):
        >>>     def test_metadata_has_correct_name(self, distribution):
        >>>         super().test_has_correct_name(distribution, "constant")
    """

    @staticmethod
    def test_has_correct_name(
        distribution: DistributionPlugin, expected_name: str
    ) -> None:
        """Test that distribution metadata has the correct name."""
        assert distribution.metadata["name"] == expected_name

    @staticmethod
    def test_has_correct_version(
        distribution: DistributionPlugin, version: str = "1.0.0"
    ) -> None:
        """Test that distribution metadata has the correct version."""
        assert distribution.metadata["version"] == version

    @staticmethod
    def test_parameter_exists(
        distribution: DistributionPlugin, param_name: str
    ) -> None:
        """Test that a parameter exists in the metadata."""
        assert param_name in distribution.metadata["parameters"]

    @staticmethod
    def test_parameter_has_type(
        distribution: DistributionPlugin, param_name: str, expected_type: str
    ) -> None:
        """Test that a parameter has the correct type."""
        assert distribution.metadata["parameters"][param_name]["type"] == expected_type

    @staticmethod
    def test_parameter_is_required(
        distribution: DistributionPlugin, param_name: str, expected_required: bool
    ) -> None:
        """Test that a parameter has the correct required flag."""
        assert (
            distribution.metadata["parameters"][param_name]["required"]
            == expected_required
        )

    @staticmethod
    def _get_parameter_description(
        distribution: DistributionPlugin, param_name: str
    ) -> str:
        """Helper to get parameter description for further assertions."""
        return distribution.metadata["parameters"][param_name]["description"]

    @staticmethod
    def test_parameter_has_description(
        distribution: DistributionPlugin, param_name: str
    ) -> None:
        """Test that a parameter has a non-empty description."""
        description = DistributionMetadataTests._get_parameter_description(
            distribution, param_name
        )
        assert len(description) > 0
