"""
Base API client with shared functionality for sync and async clients.

This module provides common functionality used by both synchronous and
asynchronous API clients to reduce code duplication.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class ApiError(Exception):
    """
    Unified API error for both sync and async clients.

    Attributes:
        message: Error message describing what went wrong
        status_code: Optional HTTP status code (if applicable)
    """

    status_code: Optional[int]

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        """
        Initialize API error.

        Args:
            message: Description of the error
            status_code: Optional HTTP status code associated with the error
        """
        super().__init__(message)
        self.status_code = status_code


class BaseAPIClient(ABC):
    """
    Base class for API clients with shared functionality.

    Provides common URL building, span attribute setting, and other
    utility methods used by both sync and async implementations.

    Attributes:
        BASE_URL: Base URL for API endpoints (empty string by default)
    """

    BASE_URL: str = ""

    @abstractmethod
    def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Implementation-specific request method.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            **kwargs: Additional request parameters

        Returns:
            Implementation-specific response object
        """
        pass

    def _build_url(self, path: str) -> str:
        """
        Build full URL from path.

        Combines BASE_URL with the provided path to create a full URL.
        Normalizes path separators to avoid double slashes.

        Args:
            path: API endpoint path (e.g., "getPrime" or "/getPrime")

        Returns:
            str: Full URL (e.g., "http://example.com/getPrime")

        Examples:
            >>> client._build_url("getPrime")
            'http://example.com/api/getPrime'
            >>> client._build_url("/api/v1/test")
            'http://example.com/api/v1/test'
        """
        # Remove leading slash from path if present
        clean_path = path.lstrip("/")
        # Remove trailing slash from BASE_URL if present
        clean_base = self.BASE_URL.rstrip("/")

        if clean_base:
            return f"{clean_base}/{clean_path}"
        return clean_path

    def _set_span_attributes(
        self,
        span: Any,
        url: str,
        method: str,
        status_code: Optional[int] = None,
    ) -> None:
        """
        Set common OpenTelemetry span attributes for HTTP requests.

        Sets standard HTTP attributes on the span for distributed tracing.

        Args:
            span: OpenTelemetry span object
            url: Full URL being requested
            method: HTTP method (GET, POST, etc.)
            status_code: Optional HTTP status code

        Note:
            This method sets attributes according to OpenTelemetry semantic
            conventions for HTTP spans.
        """
        span.set_attribute("http.url", url)
        span.set_attribute("http.method", method)

        if status_code is not None:
            span.set_attribute("http.status_code", status_code)
