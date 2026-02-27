import asyncio
import logging
import os
from typing import Any, Optional

import httpx
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from primes.config import from_env
from primes.api_client_base import ApiError, BaseAPIClient


tracer = trace.get_tracer("primes-client-async")

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


# For backward compatibility, AsyncApiError is now an alias for ApiError
AsyncApiError = ApiError


class AsyncAPIClient(BaseAPIClient):
    """Async HTTP client for API requests with retry logic and telemetry."""

    def __init__(
        self,
        timeout: float = REQUEST_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """
        Initialize async API client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.BASE_URL = from_env()["BASE_URL"]
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "AsyncAPIClient":
        """Enter context manager and create HTTP client."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close HTTP client."""
        if self._client:
            await self._client.aclose()
        self._client = None

    def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Implementation-specific request method (required by BaseAPIClient).

        Note: This is a synchronous interface for compatibility with BaseAPIClient.
        The actual async implementation is in make_api_call.

        Args:
            method: HTTP method
            url: Full URL
            **kwargs: Additional parameters

        Returns:
            Placeholder (actual requests made in make_api_call)
        """
        # Actual async implementation is in make_api_call
        # This method exists to satisfy BaseAPIClient interface
        return None

    async def _dispatch_request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
        headers: Optional[dict[str, Any]],
        call_span: Any,
    ) -> httpx.Response:
        assert self._client is not None
        if method == "GET":
            return await self._client.get(url, params=params, headers=headers)
        if method == "POST":
            return await self._client.post(url, json=data, headers=headers)
        if method == "PUT":
            return await self._client.put(url, json=data, headers=headers)
        if method == "DELETE":
            return await self._client.delete(url, headers=headers)

        call_span.set_status(Status(StatusCode.ERROR, "Unsupported HTTP method"))
        raise ValueError(f"Unsupported HTTP method: {method}")

    @staticmethod
    async def _sleep_for_retry(attempt: int) -> None:
        backoff = min(2**attempt, 10)
        await asyncio.sleep(backoff)

    @staticmethod
    def _final_error(path: str, retries: int, last_error: Optional[Exception]) -> str:
        return (
            f"Request failed after {retries + 1} attempts. "
            f"Last error: {str(last_error)} at path '{path}'"
        )

    def _record_retry(
        self,
        call_span: Any,
        attempt: int,
        error_msg: str,
        status_code: Optional[int] = None,
    ) -> ApiError:
        logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.max_retries})")
        call_span.set_attribute("http.request.retries", attempt + 1)
        return AsyncApiError(error_msg, status_code)

    def _handle_error_response(
        self,
        response: httpx.Response,
        path: str,
        attempt: int,
        call_span: Any,
    ) -> Optional[ApiError]:
        if not response.is_error:
            return None

        error_msg = f"HTTP {response.status_code}: {response.text[:200]} at path '{path}'"
        if attempt < self.max_retries:
            logger.warning(
                f"Request failed (attempt {attempt + 1}/{self.max_retries}): "
                f"{error_msg}, retrying..."
            )
            call_span.set_attribute("http.request.retries", attempt + 1)
            return AsyncApiError(error_msg, response.status_code)

        call_span.set_status(Status(StatusCode.ERROR, error_msg))
        raise AsyncApiError(error_msg, response.status_code)

    async def _attempt_request(
        self,
        method: str,
        url: str,
        path: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
        headers: Optional[dict[str, Any]],
        attempt: int,
        call_span: Any,
    ) -> tuple[Optional[httpx.Response], Optional[ApiError]]:
        try:
            response = await self._dispatch_request(
                method, url, params, data, headers, call_span
            )
            call_span.set_attribute("http.status_code", response.status_code)
            error = self._handle_error_response(response, path, attempt, call_span)
            if error is not None:
                return None, error
            call_span.set_status(Status(StatusCode.OK))
            return response, None
        except httpx.TimeoutException:
            return (
                None,
                self._record_retry(
                    call_span,
                    attempt,
                    f"Request timeout after {self.timeout}s at path '{path}'",
                ),
            )
        except httpx.NetworkError as e:
            return (
                None,
                self._record_retry(
                    call_span, attempt, f"Network error at path '{path}': {e}"
                ),
            )
        except httpx.HTTPStatusError as e:
            return (
                None,
                self._record_retry(
                    call_span,
                    attempt,
                    (
                        f"HTTP status error {e.response.status_code} at path '{path}': "
                        f"{e.response.text[:200]}"
                    ),
                    e.response.status_code,
                ),
            )
        except ValueError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error at path '{path}': {e}"
            logger.error(f"{error_msg} (attempt {attempt + 1}/{self.max_retries})")
            call_span.set_attribute("http.request.retries", attempt + 1)
            return None, AsyncApiError(error_msg)

    async def make_api_call(
        self,
        path: str,
        method: str = "GET",
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Make an async API call with retry logic and OpenTelemetry tracing.

        Args:
            path: API endpoint path (e.g., "getPrime")
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            data: Request body data for POST requests
            headers: Request headers

        Returns:
            httpx.Response: The HTTP response

        Raises:
            AsyncApiError: If the request fails after retries or returns an error status
            ValueError: If an unsupported HTTP method is provided
        """
        if not self._client:
            raise RuntimeError(
                "AsyncAPIClient must be used as a context manager "
                "(e.g., 'async with client as c:')"
            )

        url = self._build_url(path)

        with tracer.start_as_current_span("async_call_api") as call_span:
            self._set_span_attributes(call_span, url, method)
            call_span.set_attribute("http.request.retries", 0)

            last_error: Optional[ApiError] = None

            for attempt in range(self.max_retries + 1):
                response, last_error = await self._attempt_request(
                    method,
                    url,
                    path,
                    params,
                    data,
                    headers,
                    attempt,
                    call_span,
                )
                if response is not None:
                    return response
                if attempt < self.max_retries:
                    await self._sleep_for_retry(attempt)

            error_msg = self._final_error(path, self.max_retries, last_error)
            call_span.set_status(Status(StatusCode.ERROR, error_msg))
            raise AsyncApiError(error_msg, getattr(last_error, "status_code", None))


async def make_api_call(
    path: str,
    method: str = "GET",
    params: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, Any]] = None,
    timeout: float = REQUEST_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> httpx.Response:
    """
    Convenience function for making async API calls without managing client lifecycle.

    This creates a new client for each call, which is less efficient but simpler to use.
    For multiple requests, consider using AsyncAPIClient as a context manager.

    Args:
        path: API endpoint path (e.g., "getPrime")
        method: HTTP method (GET, POST, etc.)
        params: Query parameters
        data: Request body data for POST requests
        headers: Request headers
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for failed requests

    Returns:
        httpx.Response: The HTTP response

    Raises:
        AsyncApiError: If the request fails after retries or returns an error status
        ValueError: If an unsupported HTTP method is provided
    """
    async with AsyncAPIClient(timeout=timeout, max_retries=max_retries) as client:
        response: httpx.Response = await client.make_api_call(
            path=path,
            method=method,
            params=params,
            data=data,
            headers=headers,
        )
        return response
