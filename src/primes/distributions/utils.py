"""
Utility functions for distribution plugins.

This module provides common validation and conversion utilities used across
multiple distribution implementations to reduce code duplication.
"""

from typing import Any, Optional, Tuple
import math


def to_float(value: Any, default: Optional[float]) -> Optional[float]:
    """
    Convert value to float with fallback default.

    Attempts to convert int, float, or numeric string to float.
    Returns the default value if conversion fails or for unsupported types.

    Args:
        value: The value to convert (int, float, str, or any other type)
        default: The fallback value if conversion fails

    Returns:
        float: The converted value or the default

    Examples:
        >>> to_float(42, 0.0)
        42.0
        >>> to_float("3.14", 0.0)
        3.14
        >>> to_float("invalid", 5.0)
        5.0
        >>> to_float(None, 1.0)
        1.0
    """
    # Explicitly reject bool since it's a subclass of int in Python
    if isinstance(value, bool):
        return default

    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    return default


def parse_float(value: Any, default: Optional[float]) -> Tuple[Optional[float], bool]:
    """
    Parse a float value with a validity flag.

    Attempts to convert int, float, or numeric string to float and returns a tuple
    of (parsed_value, is_valid). Returns the default with False when conversion
    fails or for unsupported types. None is treated as valid and returns default.

    Args:
        value: The value to convert (int, float, str, or any other type)
        default: The fallback value if conversion fails

    Returns:
        Tuple[Optional[float], bool]: (converted value or default, valid flag)

    Examples:
        >>> parse_float(42, 0.0)
        (42.0, True)
        >>> parse_float("3.14", 0.0)
        (3.14, True)
        >>> parse_float("invalid", 5.0)
        (5.0, False)
        >>> parse_float(None, 1.0)
        (1.0, True)
    """
    if value is None:
        return default, True

    if isinstance(value, bool):
        return default, False

    if isinstance(value, (int, float, str)):
        try:
            return float(value), True
        except (ValueError, TypeError):
            return default, False

    return default, False


def validate_numeric(
    value: Optional[float],
    *,
    allow_none: bool = True,
    positive: bool = False,
    non_negative: bool = False,
    finite: bool = True,
) -> bool:
    """
    Validate a numeric value against common constraints.

    Performs comprehensive validation of numeric values including type checking,
    range validation (positive/non-negative), and finiteness checks.

    Args:
        value: The value to validate (can be None)
        allow_none: Whether None values are considered valid (default: True)
        positive: If True, value must be > 0 (default: False)
        non_negative: If True, value must be >= 0 (default: False)
        finite: If True, value must be finite (not NaN or infinity) (default: True)

    Returns:
        bool: True if value passes all specified validations, False otherwise

    Examples:
        >>> validate_numeric(5.0, positive=True)
        True
        >>> validate_numeric(0.0, positive=True)
        False
        >>> validate_numeric(None, allow_none=True)
        True
        >>> validate_numeric(float('nan'), finite=True)
        False

    Note:
        - positive and non_negative are mutually exclusive in most use cases
        - If value is None, validation passes only if allow_none=True
        - Type checking is performed before other validations
    """
    if value is None:
        return allow_none

    if not isinstance(value, (int, float)):
        return False

    if finite:
        try:
            if not math.isfinite(float(value)):
                return False
        except (TypeError, ValueError):
            return False

    if positive and value <= 0:
        return False

    if non_negative and value < 0:
        return False

    return True


def validate_config_structure(config: Any) -> bool:
    """
    Validate config is a dict if provided.

    Used by distribution plugins to validate that their config attribute
    is either None or a dictionary.

    Args:
        config: The config value to validate

    Returns:
        bool: True if config is None or a dict, False otherwise

    Examples:
        >>> validate_config_structure({"key": "value"})
        True
        >>> validate_config_structure(None)
        True
        >>> validate_config_structure("invalid")
        False
    """
    return config is None or isinstance(config, dict)


def parse_json_or_list(value: Any) -> Tuple[bool, Any]:
    """
    Parse JSON string or return list/dict as-is.

    Attempts to parse a JSON string, or validates that the input is already
    a list or dict. Used by sequence and mix distributions for parsing
    complex configuration data.

    Args:
        value: The value to parse (str, list, dict, or any other type)

    Returns:
        Tuple[bool, Any]: A tuple of (success, parsed_data)
            - success: True if parsing succeeded or value was already valid
            - parsed_data: The parsed data, or None if parsing failed

    Examples:
        >>> success, data = parse_json_or_list('[[1, 2], [3, 4]]')
        >>> success
        True
        >>> data
        [[1, 2], [3, 4]]

        >>> success, data = parse_json_or_list([[1, 2]])
        >>> success
        True
        >>> data
        [[1, 2]]

        >>> success, data = parse_json_or_list('invalid')
        >>> success
        False
        >>> data is None
        True

    Note:
        - If value is None, returns (True, None)
        - If value is already a list or dict, returns it as-is
        - Only strings are parsed as JSON
        - Malformed JSON returns (False, None)
    """
    if value is None:
        return True, None

    if isinstance(value, str):
        try:
            import json

            return True, json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return False, None

    if isinstance(value, (list, dict)):
        return True, value

    return False, None
