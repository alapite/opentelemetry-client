import json
import logging
import os
import random
import time
from urllib.parse import urlparse

import requests
from opentelemetry import trace
from openapi_spec_validator import validate
from openapi_spec_validator.exceptions import OpenAPISpecValidatorError
from requests import Response

from primes.api_client import ApiError, make_api_call
from primes.config import from_env
from primes.types import Position


tracer = trace.get_tracer("primes-client")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def request_primes(position: Position) -> Response:
    params = {"position": position}
    response = make_api_call("getPrime", "GET", params=params)
    response_val = response.json()
    logger.info(f"Prime at position {position} is {response_val}")
    return response


def load_openapi_spec(spec_url: str) -> dict:
    logger.info(f"Loading OpenAPI spec from URL '{spec_url}'")
    if spec_url.startswith("http"):
        try:
            response = requests.get(spec_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch OpenAPI spec: {e}")
            raise
    else:
        try:
            with open(spec_url, "r") as file:
                return json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load OpenAPI spec from file: {e}")
            raise


def validate_response(spec: dict, base_url: str) -> bool:
    try:
        validate(spec, base_url)
    except OpenAPISpecValidatorError as e:
        logger.error(f"Validation failed: {e}")
        return False
    return True


def _spec_has_path(spec: dict, path: str) -> bool:
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return False

    normalized = path if path.startswith("/") else f"/{path}"
    base_path = normalized.rstrip("/") or "/"

    for raw_spec_path in paths.keys():
        if not isinstance(raw_spec_path, str):
            continue

        spec_path = raw_spec_path if raw_spec_path.startswith("/") else f"/{raw_spec_path}"
        spec_path = spec_path.rstrip("/") or "/"

        if spec_path == base_path:
            return True
        if base_path != "/" and spec_path.startswith(f"{base_path}/"):
            return True

    return False


def main() -> None:
    config = from_env()
    service_url = config["SERVICE_URL"]
    base_url = config["BASE_URL"]

    spec_url = os.getenv("OPENAPI_SPEC_URL", f"{service_url}/v3/api-docs")
    try:
        openapi_spec = load_openapi_spec(spec_url)
    except Exception:
        logger.error("OpenAPI spec could not be loaded; skipping client run.")
        return

    api_path = urlparse(base_url).path or "/"
    if not _spec_has_path(openapi_spec, api_path):
        logger.warning(
            "OpenAPI spec does not contain base path '%s'; skipping client run.",
            api_path,
        )
        return

    max_position = int(os.getenv("MAX_POSITION", "2000"))
    num_requests = int(os.getenv("NUM_REQUESTS", "200"))
    sleep_time = float(os.getenv("SLEEP_TIME", "2.0"))
    validate_interval = int(os.getenv("VALIDATE_INTERVAL", "10"))

    position_list = [random.randint(0, max_position) for _ in range(num_requests)]

    for p, p_value in enumerate(position_list):
        try:
            request_primes(p_value)
        except ApiError as e:
            logger.error(
                f"API error for prime at position {p_value}: "
                f"{e} (Status: {e.status_code if e.status_code else 'N/A'})"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error for prime at position {p_value}: "
                f"{type(e).__name__}: {e}"
            )

        if (p + 1) % validate_interval == 0:
            if validate_response(openapi_spec, base_url):
                logger.info("Response is valid according to the OpenAPI specification.")
            else:
                logger.error(
                    "Response is not valid according to the OpenAPI specification."
                )

        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
