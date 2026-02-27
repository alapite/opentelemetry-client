from typing import TypedDict


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
    TELEMETRY_ENDPOINT: str | None


class Response(TypedDict):
    """API response structure for prime number requests."""

    number: int
    is_prime: bool
    time_elapsed: float


Position = int
