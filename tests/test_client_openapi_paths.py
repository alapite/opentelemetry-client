from typing import Any

from primes.client import _spec_has_path


def test_spec_has_path_accepts_exact_path_match() -> None:
    spec: dict[str, Any] = {
        "paths": {
            "/api/primes": {},
        }
    }

    assert _spec_has_path(spec, "/api/primes/")


def test_spec_has_path_accepts_operation_path_under_base_path() -> None:
    spec: dict[str, Any] = {
        "paths": {
            "/api/primes/getPrime": {},
        }
    }

    assert _spec_has_path(spec, "/api/primes/")


def test_spec_has_path_returns_false_for_non_matching_base_path() -> None:
    spec: dict[str, Any] = {
        "paths": {
            "/api/other/getPrime": {},
        }
    }

    assert not _spec_has_path(spec, "/api/primes/")
