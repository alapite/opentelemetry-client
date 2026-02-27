import json
import logging
import math
import os
import time

from locust import HttpUser, LoadTestShape, task, between
from opentelemetry import trace

from primes.config import SERVICE_URL
from primes.distributions.loader import instantiate_plugin


tracer = trace.get_tracer("primes-client")
logger = logging.getLogger(__name__)
DEFAULT_WAIT_TIME = between(0.5, 2.0)


def _load_distribution_from_env():
    distribution_json = os.getenv("PRIMES_DISTRIBUTION")
    if not distribution_json:
        return None
    try:
        payload = json.loads(distribution_json)
        name = payload.get("name")
        config = payload.get("config", {})
        if not isinstance(name, str):
            return None
        if not isinstance(config, dict):
            return None
        try:
            plugin = instantiate_plugin(name, config)
        except ValueError:
            return None
        if not plugin.validate():
            return None
        return plugin
    except Exception:
        logger.warning(
            "Failed to load distribution from PRIMES_DISTRIBUTION", exc_info=True
        )
        return None


DISTRIBUTION_PLUGIN = _load_distribution_from_env()
START_TIME = time.time()
TARGET_RPS = float(os.getenv("PRIMES_TARGET_RPS", "0") or 0)
EXPECTED_RPS_PER_USER = float(os.getenv("PRIMES_EXPECTED_RPS_PER_USER", "0.8"))


class DistributionLoadShape(LoadTestShape):
    def tick(self):
        if DISTRIBUTION_PLUGIN is None or TARGET_RPS <= 0:
            return None

        elapsed = time.time() - START_TIME
        current_rps = DISTRIBUTION_PLUGIN.get_rate(elapsed, TARGET_RPS)
        if current_rps <= 0:
            return (0, 1)

        per_user = max(0.01, EXPECTED_RPS_PER_USER)
        user_count = max(1, math.ceil(current_rps / per_user))
        spawn_rate = max(1, user_count)
        return (user_count, spawn_rate)


class PrimesUser(HttpUser):
    host = SERVICE_URL
    wait_time = DEFAULT_WAIT_TIME
    weight = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position = int(os.getenv("PRIME_POSITION", "100"))

    @task
    def get_prime(self):
        with tracer.start_as_current_span("locust_task") as span:
            span.set_attribute("position", self.position)

            try:
                response = self.client.get(
                    "/api/primes/getPrime",
                    params={"position": self.position},
                    name="/api/primes/getPrime"
                )
                span.set_attribute("http.status_code", response.status_code)

                # Log non-success responses for debugging
                if response.status_code >= 400:
                    logger.warning(
                        f"Request failed with status {response.status_code}: "
                        f"{response.text[:200]} for position {self.position}"
                    )

            except Exception as e:
                logger.error(
                    f"Exception during request for position {self.position}: "
                    f"{type(e).__name__}: {e}"
                )
                raise
