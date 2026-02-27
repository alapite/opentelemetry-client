import logging

from locust import HttpUser, task, between
from opentelemetry import trace

from primes.config import SERVICE_URL


tracer = trace.get_tracer("primes-client")
logger = logging.getLogger(__name__)


class PrimesUser(HttpUser):
    host = SERVICE_URL
    wait_time = between(0.5, 2.0)

    @task
    def get_prime(self):
        position = 100
        with tracer.start_as_current_span("locust_task") as span:
            span.set_attribute("position", position)

            try:
                response = self.client.get(
                    "/api/primes/getPrime",
                    params={"position": position},
                    name="/api/primes/getPrime"
                )
                span.set_attribute("http.status_code", response.status_code)

                # Log non-success responses for debugging
                if response.status_code >= 400:
                    logger.warning(
                        f"Request failed with status {response.status_code}: "
                        f"{response.text[:200]} for position {position}"
                    )

            except Exception as e:
                logger.error(
                    f"Exception during request for position {position}: "
                    f"{type(e).__name__}: {e}"
                )
                raise
