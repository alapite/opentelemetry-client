import asyncio
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Callable

from primes.api.connection_manager import manager
from primes.distributions.loader import instantiate_plugin
from primes.distributions.base import DistributionPlugin
from primes.async_api_client import AsyncApiError, AsyncAPIClient

logger = logging.getLogger(__name__)


@dataclass
class RunMetrics:
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    rps: float = 0.0
    avg_response_time: float = 0.0
    active_users_estimate: int = 0


@dataclass
class PluginConfig:
    name: str = "constant"
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunConfig:
    test_type: str = "linear"
    duration_seconds: Optional[int] = None
    spawn_rate: float = 10.0
    user_count: int = 1
    num_requests: Optional[int] = None
    target_rps: Optional[float] = None
    distribution: Optional[PluginConfig] = None


@dataclass
class RunState:
    test_id: str
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    config: Optional[RunConfig] = None
    metrics: RunMetrics = field(default_factory=RunMetrics)
    process: Optional[asyncio.subprocess.Process] = None
    output_lines: list[str] = field(default_factory=list)
    _in_flight_requests: int = field(default=0, repr=False)
    # Limit output lines to prevent memory issues in long-running tests
    MAX_OUTPUT_LINES: int = 10000


active_tests: Dict[str, RunState] = {}
TERMINAL_STATUSES = {"completed", "failed", "stopped"}
_LOCUST_USER_PATTERNS = (
    re.compile(r"\((\d+)\s+total users\)"),
    re.compile(r"\busers?\s*:\s*(\d+)\b", re.IGNORECASE),
)


def get_test_state(test_id: str) -> Optional[RunState]:
    return active_tests.get(test_id)


def list_active_tests() -> list[str]:
    return list(active_tests.keys())


def list_running_tests() -> list[str]:
    return [
        test_id for test_id, state in active_tests.items() if state.status == "running"
    ]


def _should_use_distribution_mode(config: RunConfig) -> bool:
    return config.distribution is not None or config.target_rps is not None


def _stop_requested(state: RunState) -> bool:
    return state.status in {"stopping", "stopped"}


async def _run_test_mode(test_id: str, config: RunConfig) -> None:
    if config.num_requests:
        if _should_use_distribution_mode(config):
            await execute_distribution_test(test_id, config)
            return
        await execute_duration_test(test_id, config)
        return
    await execute_locust_test(test_id, config)


def _finalize_test_run(state: RunState) -> None:
    state.end_time = datetime.now()
    if state.end_time and state.start_time:
        duration = (state.end_time - state.start_time).total_seconds()
        if duration > 0:
            state.metrics.rps = state.metrics.request_count / duration
    if state.status in TERMINAL_STATUSES:
        state._in_flight_requests = 0
        state.metrics.active_users_estimate = 0


def _configured_users(state: RunState) -> int:
    if state.config is None:
        return 0
    return max(0, int(state.config.user_count))


def _clamp_active_users_for_internal_modes(state: RunState) -> None:
    configured = _configured_users(state)
    if configured <= 0:
        state.metrics.active_users_estimate = max(0, state.metrics.active_users_estimate)
        return
    state.metrics.active_users_estimate = max(
        0, min(state.metrics.active_users_estimate, configured)
    )


def _increment_active_users(state: RunState) -> None:
    state._in_flight_requests += 1
    state.metrics.active_users_estimate = state._in_flight_requests
    _clamp_active_users_for_internal_modes(state)


def _decrement_active_users(state: RunState) -> None:
    state._in_flight_requests = max(0, state._in_flight_requests - 1)
    state.metrics.active_users_estimate = state._in_flight_requests
    _clamp_active_users_for_internal_modes(state)


def _set_locust_active_users_from_line(state: RunState, line: str) -> None:
    for pattern in _LOCUST_USER_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        try:
            parsed_users = int(match.group(1))
        except (TypeError, ValueError):
            continue
        state.metrics.active_users_estimate = max(0, parsed_users)
        return


async def execute_test(test_id: str, config: RunConfig) -> None:
    state = active_tests.get(test_id)
    if not state:
        logger.error(f"Test {test_id} not found in active tests")
        return

    state.status = "running"
    state.start_time = datetime.now()
    state.config = config

    try:
        await _run_test_mode(test_id, config)
        if _stop_requested(state):
            state.status = "stopped"
            logger.info(f"Test {test_id} stopped")
        else:
            state.status = "completed"
            logger.info(f"Test {test_id} completed successfully")
    except Exception as e:
        if _stop_requested(state):
            state.status = "stopped"
            logger.info(f"Test {test_id} stopped")
        else:
            state.status = "failed"
            logger.error(f"Test {test_id} failed: {e}")
    finally:
        _finalize_test_run(state)
        await manager.broadcast(test_id, format_metrics(test_id, state))


def _build_locust_command(config: RunConfig) -> list[str]:
    cmd = [
        "locust",
        "-f",
        "src/primes/tasks.py",
        "--headless",
        "--users",
        str(config.user_count),
        "--spawn-rate",
        str(config.spawn_rate),
    ]
    if config.duration_seconds:
        cmd.extend(["--run-time", f"{config.duration_seconds}s"])
    if config.num_requests:
        cmd.extend(["--num-requests", str(config.num_requests)])
    return cmd


def _distribution_payload(config: RunConfig) -> Optional[dict[str, Any]]:
    if config.distribution is not None:
        return {
            "name": config.distribution.name,
            "config": config.distribution.config,
        }
    if config.target_rps is not None:
        return {"name": "constant", "config": {}}
    return None


def _build_locust_env(config: RunConfig) -> dict[str, str]:
    env = os.environ.copy()
    distribution_payload = _distribution_payload(config)
    if distribution_payload is not None:
        env["PRIMES_DISTRIBUTION"] = json.dumps(distribution_payload)

    target_rps = config.target_rps
    if target_rps is None and distribution_payload is not None:
        target_rps = config.spawn_rate
    if target_rps is not None:
        env["PRIMES_TARGET_RPS"] = str(target_rps)
    return env


def _append_output_line(state: RunState, decoded: str) -> None:
    state.output_lines.append(decoded)
    if len(state.output_lines) > state.MAX_OUTPUT_LINES:
        state.output_lines = state.output_lines[-state.MAX_OUTPUT_LINES:]


async def _terminate_process(process: asyncio.subprocess.Process) -> None:
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()


async def _ensure_process_success(
    process: asyncio.subprocess.Process, state: RunState, test_id: str
) -> None:
    assert process.stderr is not None
    return_code = await process.wait()
    if return_code == 0:
        return
    if _stop_requested(state) and return_code in {-15, 143}:
        logger.info(
            f"Locust subprocess terminated after stop request for test {test_id}: {return_code}"
        )
        return
    stderr = await process.stderr.read()
    error_msg = stderr.decode().strip()
    logger.error(f"Locust subprocess failed with code {return_code}: {error_msg}")
    raise RuntimeError(f"Locust failed with exit code {return_code}")


async def _stream_locust_output(
    process: asyncio.subprocess.Process,
    state: RunState,
    test_id: str,
) -> None:
    assert process.stdout is not None
    assert process.stderr is not None

    queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()

    async def _read_stream(
        stream: asyncio.StreamReader,
        source: str,
    ) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            await queue.put((source, line.decode(errors="replace").strip()))
        await queue.put((source, None))

    stdout_task = asyncio.create_task(_read_stream(process.stdout, "stdout"))
    stderr_task = asyncio.create_task(_read_stream(process.stderr, "stderr"))
    closed_streams = 0
    last_broadcast = time.time()

    try:
        while closed_streams < 2:
            try:
                source, decoded = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                await manager.broadcast(test_id, format_metrics(test_id, state))
                last_broadcast = time.time()
                continue

            if decoded is None:
                closed_streams += 1
                continue

            _append_output_line(state, decoded)
            logger.debug(f"Test {test_id} {source}: {decoded}")
            _parse_metrics_from_output(state, decoded)
            _set_locust_active_users_from_line(state, decoded)

            current_time = time.time()
            if current_time - last_broadcast >= 1.0:
                await manager.broadcast(test_id, format_metrics(test_id, state))
                last_broadcast = current_time
    finally:
        stdout_task.cancel()
        stderr_task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)


async def execute_locust_test(test_id: str, config: RunConfig) -> None:
    state = active_tests[test_id]
    cmd = _build_locust_command(config)

    logger.info(f"Starting Locust subprocess for test {test_id}: {' '.join(cmd)}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        env=_build_locust_env(config),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    state.process = process

    try:
        await _stream_locust_output(process, state, test_id)
        await _ensure_process_success(process, state, test_id)
    except asyncio.CancelledError:
        logger.info(f"Test {test_id} execution cancelled, terminating subprocess")
        await _terminate_process(process)
        raise
    finally:
        await manager.broadcast(test_id, format_metrics(test_id, state))


async def _execute_prime_request(
    client: AsyncAPIClient,
    state: RunState,
    test_id: str,
    position: int,
) -> None:
    _increment_active_users(state)
    state.metrics.request_count += 1
    request_start = time.time()

    try:
        response = await client.make_api_call(
            "getPrime",
            method="GET",
            params={"position": position},
        )
        if response.status_code == 200:
            state.metrics.success_count += 1
        else:
            state.metrics.failure_count += 1
            logger.error(
                f"Request failed for test {test_id}, position {position}: "
                f"HTTP {response.status_code} - {response.text[:200]}"
            )
    except AsyncApiError as e:
        state.metrics.failure_count += 1
        logger.error(
            f"API error for test {test_id}, position {position}: "
            f"{e} (Status: {e.status_code})"
        )
    except Exception as e:
        state.metrics.failure_count += 1
        logger.error(
            f"Unexpected error for test {test_id}, position {position}: "
            f"{type(e).__name__}: {e}"
        )
    finally:
        _decrement_active_users(state)

    latency_ms = (time.time() - request_start) * 1000.0
    count = state.metrics.request_count
    prev_avg = state.metrics.avg_response_time
    state.metrics.avg_response_time = (prev_avg * (count - 1) + latency_ms) / count


def _request_cap_reached(
    state: RunState, pending: set[asyncio.Task[None]], max_requests: Optional[int]
) -> bool:
    if max_requests is None:
        return False
    return (state.metrics.request_count + len(pending)) >= max_requests


def _update_tokens(token_count: float, current_rps: float, tick_delta: float) -> float:
    if current_rps <= 0 or tick_delta <= 0:
        return token_count
    max_tokens = max(1.0, current_rps * 2)
    return min(max_tokens, token_count + current_rps * tick_delta)


async def _schedule_distribution_tasks(
    tokens: float,
    semaphore: asyncio.Semaphore,
    pending: set[asyncio.Task[None]],
    reached_cap: Callable[[], bool],
    create_task: Callable[[], asyncio.Task[None]],
) -> float:
    while tokens >= 1.0 and not semaphore.locked():
        if reached_cap():
            return 0.0
        tokens -= 1.0
        task = create_task()
        pending.add(task)
        task.add_done_callback(pending.discard)
    return tokens


def _distribution_should_stop(
    state: RunState,
    elapsed: float,
    duration_seconds: Optional[int],
    pending: set[asyncio.Task[None]],
    max_requests: Optional[int],
    test_id: str,
) -> bool:
    if state.status != "running":
        logger.info(f"Test {test_id} no longer running, stopping execution")
        return True
    if duration_seconds is not None and elapsed >= duration_seconds:
        return True
    return _request_cap_reached(state, pending, max_requests)


async def _maybe_broadcast_metrics(
    test_id: str, state: RunState, now: float, last_broadcast: float
) -> float:
    if now - last_broadcast < 1.0:
        return last_broadcast
    await manager.broadcast(test_id, format_metrics(test_id, state))
    return now


async def execute_duration_test(test_id: str, config: RunConfig) -> None:
    state = active_tests[test_id]
    position = 100
    requests_to_send = config.num_requests or 100
    spawn_rate = config.spawn_rate
    interval = 1.0 / spawn_rate if spawn_rate > 0 else 1.0
    # Fix: Ensure broadcast_every is at least 1, even for fractional spawn_rates
    broadcast_every = max(1, int(spawn_rate)) if spawn_rate >= 1.0 else 1

    logger.info(
        f"Executing duration test {test_id}: {requests_to_send} requests at {spawn_rate} req/s"
    )

    async with AsyncAPIClient() as client:
        for _ in range(requests_to_send):
            if state.status != "running":
                logger.info(f"Test {test_id} no longer running, stopping execution")
                break

            await _execute_prime_request(client, state, test_id, position)

            if (state.metrics.request_count % broadcast_every) == 0:
                await manager.broadcast(test_id, format_metrics(test_id, state))

            await asyncio.sleep(interval)

    await manager.broadcast(test_id, format_metrics(test_id, state))


async def execute_distribution_test(test_id: str, config: RunConfig) -> None:
    state = active_tests[test_id]
    position = 100
    target_rps = _get_target_rps(config)
    plugin = _create_distribution_instance(config.distribution)
    if not plugin.validate():
        raise ValueError(f"Invalid distribution config for '{plugin.metadata['name']}'")

    max_requests = config.num_requests
    duration_seconds = config.duration_seconds
    if max_requests is None and duration_seconds is None:
        raise ValueError("distribution tests require num_requests or duration_seconds")

    logger.info(
        f"Executing distribution test {test_id}: "
        f"target_rps={target_rps}, distribution={plugin.metadata['name']}"
    )

    start_time = time.time()
    last_broadcast = start_time
    last_tick = start_time
    tokens = 0.0
    max_concurrency = max(1, int(config.user_count))
    semaphore = asyncio.Semaphore(max_concurrency)
    pending: set[asyncio.Task[None]] = set()

    async def _run_request(client: AsyncAPIClient) -> None:
        async with semaphore:
            await _execute_prime_request(client, state, test_id, position)

    async with AsyncAPIClient() as client:
        def _reached_cap() -> bool:
            return _request_cap_reached(state, pending, max_requests)

        def _create_task() -> asyncio.Task[None]:
            return asyncio.create_task(_run_request(client))

        while True:
            now = time.time()
            elapsed = now - start_time
            if _distribution_should_stop(
                state, elapsed, duration_seconds, pending, max_requests, test_id
            ):
                break

            current_rps = plugin.get_rate(elapsed, target_rps)
            state.metrics.rps = current_rps
            tick_delta = now - last_tick
            last_tick = now

            tokens = _update_tokens(tokens, current_rps, tick_delta)

            if current_rps <= 0:
                await asyncio.sleep(0.25)
                continue

            tokens = await _schedule_distribution_tasks(
                tokens, semaphore, pending, _reached_cap, _create_task
            )

            last_broadcast = await _maybe_broadcast_metrics(
                test_id, state, now, last_broadcast
            )

            await asyncio.sleep(0.01)

    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    await manager.broadcast(test_id, format_metrics(test_id, state))


def _parse_metrics_from_output(state: RunState, line: str) -> None:
    parsed_rps = _parse_rps_from_line(line)
    if parsed_rps is not None:
        state.metrics.rps = parsed_rps

    aggregated = _parse_aggregated_metrics(line)
    if aggregated is None:
        return

    total_requests, total_failures, total_successes, reqs_per_sec = aggregated
    if total_requests >= state.metrics.request_count:
        state.metrics.request_count = total_requests
    if total_failures >= state.metrics.failure_count:
        state.metrics.failure_count = total_failures
    if total_successes >= state.metrics.success_count:
        state.metrics.success_count = total_successes
    if reqs_per_sec is not None:
        state.metrics.rps = reqs_per_sec


def _parse_rps_from_line(line: str) -> Optional[float]:
    rps_match = re.search(r"\bRPS:\s*([0-9]+(?:\.[0-9]+)?)", line)
    if not rps_match:
        return None
    try:
        return float(rps_match.group(1))
    except ValueError:
        return None


def _parse_aggregated_metrics(
    line: str,
) -> Optional[tuple[int, int, int, Optional[float]]]:
    normalized = line.strip()
    if "Aggregated" not in normalized:
        return None

    parts = normalized.split()
    try:
        aggregated_index = parts.index("Aggregated")
        total_requests = int(parts[aggregated_index + 1])
        failures_raw = parts[aggregated_index + 2].split("(", maxsplit=1)[0]
        total_failures = int(failures_raw)
    except (ValueError, IndexError) as exc:
        logger.debug("Unable to parse locust metrics line '%s': %s", line, exc)
        return None

    total_successes = max(0, total_requests - total_failures)
    reqs_per_sec = _parse_aggregated_rps(parts[aggregated_index + 1 :])
    return total_requests, total_failures, total_successes, reqs_per_sec


def _parse_aggregated_rps(aggregated_tail: list[str]) -> Optional[float]:
    if len(aggregated_tail) < 2:
        return None
    try:
        reqs_per_sec = float(aggregated_tail[-2])
    except ValueError:
        return None
    if reqs_per_sec < 0:
        return None
    return reqs_per_sec


def format_metrics(test_id: str, state: RunState) -> dict:
    configured_users = _configured_users(state)
    active_users_estimate = max(0, int(state.metrics.active_users_estimate))

    if state.process is not None and state.status == "running" and active_users_estimate == 0:
        active_users_estimate = configured_users
    if state.status in TERMINAL_STATUSES:
        active_users_estimate = 0

    return {
        "type": "metrics",
        "test_id": test_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": state.status,
        "data": {
            "requests_sent": state.metrics.request_count,
            "responses_received": state.metrics.success_count,
            "errors": state.metrics.failure_count,
            "rps": round(state.metrics.rps, 2),
            "avg_latency_ms": round(state.metrics.avg_response_time, 2),
            "active_users_estimate": active_users_estimate,
            "configured_users": configured_users,
        },
    }


async def stop_test(test_id: str) -> bool:
    state = active_tests.get(test_id)
    if not state:
        return False

    if state.status in TERMINAL_STATUSES or state.status == "stopping":
        return True

    state.status = "stopping"

    if state.process:
        await _terminate_process(state.process)
        state.process = None

    state.status = "stopped"
    state.metrics.active_users_estimate = 0
    state._in_flight_requests = 0
    state.end_time = datetime.now()
    logger.info(f"Test {test_id} stopped")
    await manager.broadcast(test_id, format_metrics(test_id, state))
    return True


def create_test(config: RunConfig) -> str:
    test_id = str(uuid.uuid4())
    state = RunState(test_id=test_id, config=config)
    active_tests[test_id] = state
    logger.info(f"Created test {test_id} with config: {asdict(config)}")
    return test_id


def _get_target_rps(config: RunConfig) -> float:
    if config.target_rps is not None:
        return float(config.target_rps)
    return float(config.spawn_rate)


def _create_distribution_instance(
    config: Optional[PluginConfig],
) -> DistributionPlugin:
    if config is None:
        config = PluginConfig(name="constant")
    return instantiate_plugin(config.name, config.config or {})
