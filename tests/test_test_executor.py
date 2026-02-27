import asyncio
from types import SimpleNamespace
from typing import cast

from primes.api import test_executor
from primes.distributions.base import DistributionPlugin
from primes.distributions.registry import registry


class DummyResponse:
    def __init__(self, status_code: int = 200, text: str = "ok") -> None:
        self.status_code = status_code
        self.text = text


class FakeAsyncAPIClient:
    async def __aenter__(self) -> "FakeAsyncAPIClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    async def make_api_call(self, *args, **kwargs) -> DummyResponse:
        return DummyResponse(200, "ok")


class DummyDistribution(DistributionPlugin):
    _metadata = {
        "name": "dummy",
        "version": "1.0.0",
        "description": "dummy",
        "author": "tests",
        "parameters": {},
    }

    @property
    def metadata(self):
        return self._metadata

    def initialize(self, config):
        self.config = config

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        return target_rps

    def validate(self) -> bool:
        return True


class FakeProcess:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return 0


class BlockingClient:
    def __init__(self, started: asyncio.Event, release: asyncio.Event) -> None:
        self.started = started
        self.release = release

    async def make_api_call(self, *args, **kwargs) -> DummyResponse:
        self.started.set()
        await self.release.wait()
        return DummyResponse(200, "ok")


def _register_dummy_plugin() -> dict[str, type]:
    saved = registry._plugins.copy()
    registry.register("dummy", DummyDistribution)
    return saved


def test_execute_test_branches_to_correct_paths(monkeypatch):
    test_executor.active_tests.clear()

    called = {"duration": 0, "distribution": 0, "locust": 0}

    async def _duration(*_args, **_kwargs):
        called["duration"] += 1

    async def _distribution(*_args, **_kwargs):
        called["distribution"] += 1

    async def _locust(*_args, **_kwargs):
        called["locust"] += 1

    monkeypatch.setattr(test_executor, "execute_duration_test", _duration)
    monkeypatch.setattr(test_executor, "execute_distribution_test", _distribution)
    monkeypatch.setattr(test_executor, "execute_locust_test", _locust)

    duration_config = test_executor.RunConfig(num_requests=5)
    duration_id = test_executor.create_test(duration_config)
    asyncio.run(test_executor.execute_test(duration_id, duration_config))

    distribution_config = test_executor.RunConfig(
        num_requests=5, target_rps=10.0, distribution=test_executor.PluginConfig()
    )
    distribution_id = test_executor.create_test(distribution_config)
    asyncio.run(test_executor.execute_test(distribution_id, distribution_config))

    locust_config = test_executor.RunConfig(num_requests=None)
    locust_id = test_executor.create_test(locust_config)
    asyncio.run(test_executor.execute_test(locust_id, locust_config))

    assert called["duration"] == 1
    assert called["distribution"] == 1
    assert called["locust"] == 1


def test_execute_duration_test_updates_metrics_and_broadcasts(monkeypatch):
    test_executor.active_tests.clear()
    test_id = "duration-test"
    config = test_executor.RunConfig(num_requests=3, spawn_rate=10.0)
    state = test_executor.RunState(test_id=test_id, status="running", config=config)
    test_executor.active_tests[test_id] = state

    async def _noop_sleep(_):
        return None

    broadcasts = []

    async def _capture_broadcast(_test_id, message):
        broadcasts.append(message)

    monkeypatch.setattr(test_executor, "AsyncAPIClient", FakeAsyncAPIClient)
    monkeypatch.setattr(test_executor.asyncio, "sleep", _noop_sleep)
    monkeypatch.setattr(test_executor.manager, "broadcast", _capture_broadcast)

    asyncio.run(test_executor.execute_duration_test(test_id, config))

    assert state.metrics.request_count == 3
    assert state.metrics.success_count == 3
    assert state.metrics.failure_count == 0
    assert broadcasts


def test_execute_distribution_test_respects_num_requests(monkeypatch):
    test_executor.active_tests.clear()
    saved_registry = _register_dummy_plugin()

    test_id = "distribution-test"
    config = test_executor.RunConfig(
        num_requests=2,
        target_rps=2.0,
        distribution=test_executor.PluginConfig(name="dummy", config={}),
    )
    state = test_executor.RunState(test_id=test_id, status="running", config=config)
    test_executor.active_tests[test_id] = state

    class FakeTime:
        def __init__(self):
            self.current = 0.0

        def __call__(self):
            self.current += 0.5
            return self.current

    fake_time = FakeTime()

    async def _capture_broadcast(_test_id, _message):
        return None

    monkeypatch.setattr(test_executor, "AsyncAPIClient", FakeAsyncAPIClient)
    monkeypatch.setattr(test_executor.time, "time", fake_time)
    monkeypatch.setattr(test_executor.manager, "broadcast", _capture_broadcast)

    try:
        asyncio.run(test_executor.execute_distribution_test(test_id, config))

        assert state.metrics.request_count == 2
        assert state.metrics.success_count == 2
        assert state.metrics.failure_count == 0
    finally:
        registry._plugins = saved_registry


def test_format_metrics_includes_status_and_live_fields():
    config = test_executor.RunConfig(user_count=6)
    state = test_executor.RunState(
        test_id="format-test",
        status="running",
        config=config,
        metrics=test_executor.RunMetrics(
            request_count=12,
            success_count=10,
            failure_count=2,
            rps=8.37,
            avg_response_time=123.456,
        ),
    )
    state.process = FakeProcess()

    payload = test_executor.format_metrics("format-test", state)
    assert payload["type"] == "metrics"
    assert payload["test_id"] == "format-test"
    assert payload["status"] == "running"
    assert payload["data"]["requests_sent"] == 12
    assert payload["data"]["responses_received"] == 10
    assert payload["data"]["errors"] == 2
    assert payload["data"]["rps"] == 8.37
    assert payload["data"]["avg_latency_ms"] == 123.46
    assert payload["data"]["configured_users"] == 6
    assert payload["data"]["active_users_estimate"] == 6


def test_parse_metrics_from_aggregated_output_updates_totals_and_rps():
    state = test_executor.RunState(test_id="parse-test", status="running")

    test_executor._parse_metrics_from_output(
        state, "Aggregated 120 3(2.50%) 145 10 300 120 9.8 0.2"
    )

    assert state.metrics.request_count == 120
    assert state.metrics.failure_count == 3
    assert state.metrics.success_count == 117
    assert state.metrics.rps == 9.8


def test_parse_metrics_from_aggregated_output_never_decreases_totals():
    state = test_executor.RunState(
        test_id="parse-guard-test",
        status="running",
        metrics=test_executor.RunMetrics(
            request_count=200,
            success_count=180,
            failure_count=20,
            rps=10.0,
        ),
    )

    test_executor._parse_metrics_from_output(
        state, "Aggregated 120 3(2.50%) 145 10 300 120 9.8 0.2"
    )

    assert state.metrics.request_count == 200
    assert state.metrics.failure_count == 20
    assert state.metrics.success_count == 180


def test_parse_metrics_from_prefixed_aggregated_output_updates_totals():
    state = test_executor.RunState(test_id="prefixed-parse-test", status="running")

    test_executor._parse_metrics_from_output(
        state,
        "[2026-02-24 19:00:00,000] host/INFO/locust.stats: "
        "Aggregated 42 1(2.38%) 145 10 300 120 9.8 0.2",
    )

    assert state.metrics.request_count == 42
    assert state.metrics.failure_count == 1
    assert state.metrics.success_count == 41
    assert state.metrics.rps == 9.8


def test_stream_locust_output_broadcasts_when_no_log_lines(monkeypatch):
    state = test_executor.RunState(test_id="silent-locust", status="running")
    broadcasts = []

    async def _run() -> None:
        stdout = asyncio.StreamReader()
        stderr = asyncio.StreamReader()
        process = SimpleNamespace(stdout=stdout, stderr=stderr)

        async def _capture_broadcast(_test_id, message):
            broadcasts.append(message)
            stdout.feed_eof()
            stderr.feed_eof()

        monkeypatch.setattr(test_executor.manager, "broadcast", _capture_broadcast)
        await test_executor._stream_locust_output(
            cast(asyncio.subprocess.Process, process),
            state,
            "silent-locust",
        )

    asyncio.run(_run())
    assert broadcasts


def test_ensure_process_success_allows_stop_sigterm():
    class FailingProcess:
        def __init__(self) -> None:
            self.stderr = asyncio.StreamReader()
            self.stderr.feed_data(b"terminated")
            self.stderr.feed_eof()

        async def wait(self) -> int:
            return -15

    async def _run() -> None:
        state = test_executor.RunState(test_id="sigterm-stop", status="stopping")
        await test_executor._ensure_process_success(
            cast(asyncio.subprocess.Process, FailingProcess()),
            state,
            "sigterm-stop",
        )

    asyncio.run(_run())


def test_execute_prime_request_updates_active_users_estimate():
    state = test_executor.RunState(
        test_id="active-users",
        status="running",
        config=test_executor.RunConfig(user_count=1),
    )
    started = asyncio.Event()
    release = asyncio.Event()
    client = BlockingClient(started, release)

    async def _run() -> None:
        task = asyncio.create_task(
            test_executor._execute_prime_request(client, state, "active-users", 100)
        )
        await started.wait()
        assert state.metrics.active_users_estimate == 1
        release.set()
        await task

    asyncio.run(_run())
    assert state.metrics.active_users_estimate == 0


def test_execute_test_broadcasts_completed_status(monkeypatch):
    test_executor.active_tests.clear()
    test_id = "final-broadcast"
    config = test_executor.RunConfig(num_requests=1, user_count=2)
    state = test_executor.RunState(test_id=test_id, status="pending", config=config)
    test_executor.active_tests[test_id] = state
    broadcasts = []

    async def _run_mode(_test_id, _config):
        state.metrics.request_count = 1
        state.metrics.success_count = 1

    async def _capture_broadcast(_test_id, message):
        broadcasts.append(message)

    monkeypatch.setattr(test_executor, "_run_test_mode", _run_mode)
    monkeypatch.setattr(test_executor.manager, "broadcast", _capture_broadcast)

    asyncio.run(test_executor.execute_test(test_id, config))
    assert broadcasts
    assert broadcasts[-1]["status"] == "completed"
    assert broadcasts[-1]["data"]["configured_users"] == 2


def test_execute_test_marks_stopped_when_stop_requested(monkeypatch):
    test_executor.active_tests.clear()
    test_id = "stopped-final-broadcast"
    config = test_executor.RunConfig(num_requests=1, user_count=2)
    state = test_executor.RunState(test_id=test_id, status="pending", config=config)
    test_executor.active_tests[test_id] = state
    broadcasts = []

    async def _run_mode(_test_id, _config):
        state.status = "stopping"
        raise RuntimeError("Locust failed with exit code -15")

    async def _capture_broadcast(_test_id, message):
        broadcasts.append(message)

    monkeypatch.setattr(test_executor, "_run_test_mode", _run_mode)
    monkeypatch.setattr(test_executor.manager, "broadcast", _capture_broadcast)

    asyncio.run(test_executor.execute_test(test_id, config))
    assert broadcasts
    assert state.status == "stopped"
    assert broadcasts[-1]["status"] == "stopped"


def test_stop_test_terminates_process():
    test_executor.active_tests.clear()
    test_id = "stop-test"
    state = test_executor.RunState(test_id=test_id, status="running")
    process = FakeProcess()
    state.process = process
    test_executor.active_tests[test_id] = state

    result = asyncio.run(test_executor.stop_test(test_id))

    assert result is True
    assert state.status == "stopped"
    assert process.terminated is True


def test_stop_test_broadcasts_stopped_status(monkeypatch):
    test_executor.active_tests.clear()
    test_id = "stop-broadcast"
    state = test_executor.RunState(test_id=test_id, status="running")
    state.process = FakeProcess()
    test_executor.active_tests[test_id] = state
    broadcasts = []

    async def _capture_broadcast(_test_id, message):
        broadcasts.append(message)

    monkeypatch.setattr(test_executor.manager, "broadcast", _capture_broadcast)

    result = asyncio.run(test_executor.stop_test(test_id))
    assert result is True
    assert broadcasts
    assert broadcasts[-1]["status"] == "stopped"
