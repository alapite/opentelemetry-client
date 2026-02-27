from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class CoreSettings:
    service_url: str
    base_url: str
    num_requests: int
    wait_time: float
    spawn_rate: float
    locust_mode: str
    workers: int
    telemetry_endpoint: Optional[str]


@dataclass(frozen=True)
class ApiSettings:
    api_server_host: str
    api_server_port: int
    api_workers: int
    presets_file: str


VALID_LOCUST_MODES = ["standalone", "distributed"]


def load_core_settings() -> CoreSettings:
    service_url = os.getenv("SERVICE_URL", "http://localhost:8080")
    base_url = f"{service_url}/api/primes"
    return CoreSettings(
        service_url=service_url,
        base_url=base_url,
        num_requests=int(os.getenv("NUM_REQUESTS", "100")),
        wait_time=float(os.getenv("WAIT_TIME", "1.0")),
        spawn_rate=float(os.getenv("SPAWN_RATE", "10.0")),
        locust_mode=os.getenv("LOCUST_MODE", "standalone"),
        workers=int(os.getenv("WORKERS", "1")),
        telemetry_endpoint=os.getenv("TELEMETRY_ENDPOINT", None),
    )


def load_api_settings() -> ApiSettings:
    return ApiSettings(
        api_server_host=os.getenv("API_SERVER_HOST", "0.0.0.0"),
        api_server_port=int(os.getenv("API_SERVER_PORT", "8000")),
        api_workers=int(os.getenv("API_WORKERS", "1")),
        presets_file=os.getenv("PRESETS_FILE", "data/presets.json"),
    )
