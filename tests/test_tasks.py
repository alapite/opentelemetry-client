import importlib
import json
import sys
import types

from primes.distributions.registry import registry


class DummyDistribution:
    metadata = {
        "name": "dummy",
        "version": "1.0.0",
        "description": "dummy",
        "author": "tests",
        "parameters": {},
    }

    def initialize(self, config):
        self.config = config

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        return target_rps

    def validate(self) -> bool:
        return True


def _reload_tasks():
    fake_locust = types.ModuleType("locust")

    class _HttpUser:
        def __init__(self, *args, **kwargs):
            pass

    class _LoadTestShape:
        def tick(self):
            return None

    def _task(func):
        return func

    def _between(*_args, **_kwargs):
        return None

    fake_locust.HttpUser = _HttpUser
    fake_locust.LoadTestShape = _LoadTestShape
    fake_locust.task = _task
    fake_locust.between = _between

    sys.modules["locust"] = fake_locust

    if "primes.tasks" in sys.modules:
        return importlib.reload(sys.modules["primes.tasks"])
    return importlib.import_module("primes.tasks")


def test_distribution_load_shape_returns_none_without_distribution(monkeypatch):
    monkeypatch.delenv("PRIMES_DISTRIBUTION", raising=False)
    monkeypatch.delenv("PRIMES_TARGET_RPS", raising=False)
    tasks = _reload_tasks()

    assert tasks.DISTRIBUTION_PLUGIN is None
    assert tasks.DistributionLoadShape().tick() is None


def test_distribution_load_shape_uses_env_distribution(monkeypatch):
    saved_registry = registry._plugins.copy()
    registry.register("dummy", DummyDistribution)

    try:
        monkeypatch.setenv(
            "PRIMES_DISTRIBUTION",
            json.dumps({"name": "dummy", "config": {}}),
        )
        monkeypatch.setenv("PRIMES_TARGET_RPS", "10")
        monkeypatch.setenv("PRIMES_EXPECTED_RPS_PER_USER", "2")

        tasks = _reload_tasks()

        assert tasks.DISTRIBUTION_PLUGIN is not None
        assert tasks.DistributionLoadShape().tick() == (5, 5)
    finally:
        registry._plugins = saved_registry
