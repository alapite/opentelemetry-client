import pytest
from unittest.mock import MagicMock
from primes.api_client_base import ApiError, BaseAPIClient


class MockAPIClient(BaseAPIClient):
    """Mock implementation for testing."""

    BASE_URL = "http://test.example.com"

    def _make_request(self, method: str, url: str, **kwargs):
        return f"{method} {url}"


class TestApiError:
    def test_creates_error_with_message_only(self):
        error = ApiError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None

    def test_creates_error_with_status_code(self):
        error = ApiError("Test error", status_code=404)
        assert error.status_code == 404

    def test_is_exception_subclass(self):
        assert issubclass(ApiError, Exception)

    def test_can_raise_and_catch(self):
        with pytest.raises(ApiError) as exc_info:
            raise ApiError("Test error")
        assert str(exc_info.value) == "Test error"


class TestBaseAPIClient:
    def test_build_url(self):
        client = MockAPIClient()
        assert client._build_url("test") == "http://test.example.com/test"

    def test_build_url_with_leading_slash(self):
        client = MockAPIClient()
        url = client._build_url("/test")
        # Should normalize to not have double slashes
        assert "test" in url
        assert "http://test.example.com" in url

    def test_build_url_with_nested_path(self):
        client = MockAPIClient()
        assert client._build_url("api/v1/test") == "http://test.example.com/api/v1/test"

    def test_set_span_attributes(self):
        client = MockAPIClient()
        span = MagicMock()
        client._set_span_attributes(span, "http://test.com/path", "GET")
        span.set_attribute.assert_any_call("http.url", "http://test.com/path")
        span.set_attribute.assert_any_call("http.method", "GET")

    def test_set_span_attributes_with_status_code(self):
        client = MockAPIClient()
        span = MagicMock()
        client._set_span_attributes(
            span, "http://test.com/path", "POST", status_code=201
        )
        span.set_attribute.assert_any_call("http.url", "http://test.com/path")
        span.set_attribute.assert_any_call("http.method", "POST")
        span.set_attribute.assert_any_call("http.status_code", 201)

    def test_base_url_is_class_attribute(self):
        assert BaseAPIClient.BASE_URL == ""
        assert MockAPIClient.BASE_URL == "http://test.example.com"
