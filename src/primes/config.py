import logging
from typing import TypedDict, Optional

from primes.settings import load_core_settings, VALID_LOCUST_MODES

logger = logging.getLogger(__name__)


class LoadTestConfig(TypedDict):
    num_requests: int
    wait_time: float
    spawn_rate: float


class Config(TypedDict):
    SERVICE_URL: str
    BASE_URL: str
    LOAD_TEST_CONFIG: LoadTestConfig
    LOCUST_MODE: str
    WORKERS: int
    TELEMETRY_ENDPOINT: Optional[str]


_CORE_SETTINGS = load_core_settings()

SERVICE_URL: str = _CORE_SETTINGS.service_url
BASE_URL: str = _CORE_SETTINGS.base_url

LOAD_TEST_CONFIG: LoadTestConfig = {
    "num_requests": _CORE_SETTINGS.num_requests,
    "wait_time": _CORE_SETTINGS.wait_time,
    "spawn_rate": _CORE_SETTINGS.spawn_rate,
}

LOCUST_MODE: str = _CORE_SETTINGS.locust_mode
WORKERS: int = _CORE_SETTINGS.workers
TELEMETRY_ENDPOINT: Optional[str] = _CORE_SETTINGS.telemetry_endpoint


def validate() -> bool:
    settings = load_core_settings()
    if settings.locust_mode not in VALID_LOCUST_MODES:
        logger.error(
            f"Invalid LOCUST_MODE '{settings.locust_mode}'. "
            f"Valid modes: {VALID_LOCUST_MODES}"
        )
        return False
    return True


def from_env() -> Config:
    settings = load_core_settings()
    return Config(
        SERVICE_URL=settings.service_url,
        BASE_URL=settings.base_url,
        LOAD_TEST_CONFIG={
            "num_requests": settings.num_requests,
            "wait_time": settings.wait_time,
            "spawn_rate": settings.spawn_rate,
        },
        LOCUST_MODE=settings.locust_mode,
        WORKERS=settings.workers,
        TELEMETRY_ENDPOINT=settings.telemetry_endpoint,
    )
