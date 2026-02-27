import logging
import os
from typing import Any, Optional

import requests
from opentelemetry import trace
from requests import Response

from primes.config import from_env
from primes.api_client_base import ApiError, BaseAPIClient


tracer = trace.get_tracer("primes-client")

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))


class SyncAPIClient(BaseAPIClient):
    """Sync HTTP client for API requests with telemetry."""

    def __init__(self) -> None:
        self.BASE_URL = from_env()["BASE_URL"]

    def _make_request(self, method: str, url: str, **kwargs) -> Response:
        if method == "GET":
            return requests.get(url, **kwargs)
        if method == "POST":
            return requests.post(url, **kwargs)
        raise ValueError(f"Unsupported HTTP method: {method}")

    def make_api_call(
        self,
        path: str,
        method: str = "GET",
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> Response:
        with tracer.start_as_current_span("call_api") as call_span:
            url = self._build_url(path)
            self._set_span_attributes(call_span, url, method)

            try:
                if method == "GET":
                    response = self._make_request(
                        method,
                        url,
                        params=params,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                    )
                elif method == "POST":
                    response = self._make_request(
                        method,
                        url,
                        json=data,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                    )
                else:
                    call_span.set_attribute("call.completed", False)
                    raise ValueError(f"Unsupported HTTP method: {method}")

                call_span.set_attribute("http.status_code", response.status_code)

                if not response.ok:
                    call_span.set_attribute("call.completed", False)
                    raise ApiError(
                        f"HTTP {response.status_code}: {response.text[:200]} at path '{path}' with method '{method}'",
                        response.status_code,
                    )

                call_span.set_attribute("call.completed", True)
                return response

            except requests.RequestException as e:
                call_span.set_attribute("call.completed", False)
                call_span.set_attribute("error.type", type(e).__name__)
                error_msg = (
                    f"Request failed for path '{path}' with method '{method}': "
                    f"{type(e).__name__}: {e}"
                )
                logger.error(error_msg)
                raise ApiError(error_msg) from e


def make_api_call(
    path: str,
    method: str = "GET",
    params: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, Any]] = None,
) -> Response:
    client = SyncAPIClient()
    return client.make_api_call(
        path,
        method=method,
        params=params,
        data=data,
        headers=headers,
    )
