import requests
import pytest

from primes.api_client import ApiError, make_api_call


class DummyResponse:
    def __init__(self, status_code: int, ok: bool, text: str) -> None:
        self.status_code = status_code
        self.ok = ok
        self.text = text


def test_make_api_call_unsupported_method():
    with pytest.raises(ValueError):
        make_api_call("getPrime", method="PATCH")


def test_make_api_call_raises_api_error_on_http_failure(monkeypatch):
    def _fake_get(*_args, **_kwargs):
        return DummyResponse(status_code=500, ok=False, text="boom")

    monkeypatch.setattr(requests, "get", _fake_get)

    with pytest.raises(ApiError):
        make_api_call("getPrime", method="GET")


def test_make_api_call_raises_api_error_on_request_exception(monkeypatch):
    def _fake_get(*_args, **_kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(requests, "get", _fake_get)

    with pytest.raises(ApiError):
        make_api_call("getPrime", method="GET")
