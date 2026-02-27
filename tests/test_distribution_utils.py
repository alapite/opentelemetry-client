from primes.distributions.utils import (
    to_float,
    parse_float,
    validate_numeric,
    validate_config_structure,
    parse_json_or_list,
)


class TestToFloat:
    def test_converts_int_to_float(self):
        assert to_float(42, 0.0) == 42.0

    def test_converts_float_to_float(self):
        assert to_float(3.14, 0.0) == 3.14

    def test_converts_numeric_string_to_float(self):
        assert to_float("2.718", 0.0) == 2.718

    def test_returns_default_for_none(self):
        assert to_float(None, 1.0) == 1.0

    def test_returns_default_for_invalid_string(self):
        assert to_float("invalid", 5.0) == 5.0

    def test_returns_default_for_dict(self):
        assert to_float({"key": "value"}, 10.0) == 10.0

    def test_returns_default_for_list(self):
        assert to_float([1, 2, 3], 0.0) == 0.0

    def test_returns_default_for_bool(self):
        assert to_float(True, 0.0) == 0.0


class TestValidateNumeric:
    def test_accepts_positive_int(self):
        assert validate_numeric(5.0, positive=True) is True

    def test_rejects_zero_for_positive(self):
        assert validate_numeric(0.0, positive=True) is False

    def test_rejects_negative_for_positive(self):
        assert validate_numeric(-1.0, positive=True) is False

    def test_accepts_zero_for_non_negative(self):
        assert validate_numeric(0.0, non_negative=True) is True

    def test_accepts_positive_for_non_negative(self):
        assert validate_numeric(5.0, non_negative=True) is True

    def test_rejects_negative_for_non_negative(self):
        assert validate_numeric(-1.0, non_negative=True) is False

    def test_rejects_nan(self):
        assert validate_numeric(float("nan"), finite=True) is False

    def test_rejects_infinity(self):
        assert validate_numeric(float("inf"), finite=True) is False

    def test_rejects_negative_infinity(self):
        assert validate_numeric(float("-inf"), finite=True) is False

    def test_accepts_none_when_allowed(self):
        assert validate_numeric(None, allow_none=True) is True

    def test_rejects_none_when_not_allowed(self):
        assert validate_numeric(None, allow_none=False) is False

    def test_rejects_string(self):
        assert validate_numeric("5.0") is False

    def test_rejects_dict(self):
        assert validate_numeric({"key": "value"}) is False

    def test_accepts_finite_positive_with_all_constraints(self):
        assert validate_numeric(5.0, positive=True, finite=True) is True

    def test_default_params_allow_none_and_finite(self):
        assert validate_numeric(None) is True
        assert validate_numeric(5.0) is True


class TestParseFloat:
    def test_parses_int(self):
        value, parsed = parse_float(42, 0.0)
        assert value == 42.0
        assert parsed is True

    def test_parses_float_string(self):
        value, parsed = parse_float("2.5", 0.0)
        assert value == 2.5
        assert parsed is True

    def test_returns_default_for_none(self):
        value, parsed = parse_float(None, 1.0)
        assert value == 1.0
        assert parsed is True

    def test_returns_default_and_false_for_invalid(self):
        value, parsed = parse_float("invalid", 5.0)
        assert value == 5.0
        assert parsed is False

    def test_returns_default_and_false_for_bool(self):
        value, parsed = parse_float(True, 0.0)
        assert value == 0.0
        assert parsed is False


class TestValidateConfigStructure:
    def test_accepts_dict(self):
        assert validate_config_structure({"key": "value"}) is True

    def test_accepts_none(self):
        assert validate_config_structure(None) is True

    def test_rejects_string(self):
        assert validate_config_structure("config") is False

    def test_rejects_list(self):
        assert validate_config_structure(["item"]) is False

    def test_rejects_int(self):
        assert validate_config_structure(42) is False

    def test_rejects_bool(self):
        assert validate_config_structure(True) is False


class TestParseJsonOrList:
    def test_parses_valid_json_string(self):
        success, data = parse_json_or_list("[[1, 2], [3, 4]]")
        assert success is True
        assert data == [[1, 2], [3, 4]]

    def test_returns_list_as_is(self):
        success, data = parse_json_or_list([[1, 2], [3, 4]])
        assert success is True
        assert data == [[1, 2], [3, 4]]

    def test_returns_none_for_none_input(self):
        success, data = parse_json_or_list(None)
        assert success is True
        assert data is None

    def test_fails_on_invalid_json(self):
        success, data = parse_json_or_list("invalid json")
        assert success is False
        assert data is None

    def test_succeeds_on_dict_json(self):
        success, data = parse_json_or_list('{"key": "value"}')
        assert success is True
        assert data == {"key": "value"}

    def test_fails_on_non_string_non_list(self):
        success, data = parse_json_or_list(42)
        assert success is False
        assert data is None

    def test_fails_on_bool(self):
        success, data = parse_json_or_list(True)
        assert success is False
        assert data is None

    def test_parses_json_array_of_objects(self):
        json_str = '[{"name": "test", "value": 42}]'
        success, data = parse_json_or_list(json_str)
        assert success is True
        assert data == [{"name": "test", "value": 42}]
