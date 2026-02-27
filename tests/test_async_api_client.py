import asyncio

import httpx
import pytest

from primes.async_api_client import AsyncAPIClient, AsyncApiError


class FakeAsyncClient:
    def __init__(self, responses=None, exceptions=None) -> None:
        self.responses = responses or []
        self.exceptions = exceptions or []
        self.calls = 0

    async def get(self, *_args, **_kwargs):
        return await self._next()

    async def post(self, *_args, **_kwargs):
        return await self._next()

    async def put(self, *_args, **_kwargs):
        return await self._next()

    async def delete(self, *_args, **_kwargs):
        return await self._next()

    async def aclose(self) -> None:
        return None

    async def _next(self):
        self.calls += 1
        if self.exceptions:
            raise self.exceptions.pop(0)
        if self.responses:
            return self.responses.pop(0)
        raise RuntimeError("No more fake responses configured")


def _response(status_code: int) -> httpx.Response:
    request = httpx.Request("GET", "http://example.local")
    return httpx.Response(status_code=status_code, request=request, content=b"data")


def test_async_api_client_retries_then_success(monkeypatch):
    fake = FakeAsyncClient(
        responses=[_response(500), _response(500), _response(200)]
    )

    async def _noop_sleep(_):
        return None

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: fake)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    async def _run():
        async with AsyncAPIClient(max_retries=2) as client:
            response = await client.make_api_call("getPrime")
            return response.status_code

    status = asyncio.run(_run())
    assert status == 200
    assert fake.calls == 3


def test_async_api_client_retries_exhausted(monkeypatch):
    fake = FakeAsyncClient(
        responses=[_response(500), _response(500), _response(500)]
    )

    async def _noop_sleep(_):
        return None

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: fake)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    async def _run():
        async with AsyncAPIClient(max_retries=2) as client:
            await client.make_api_call("getPrime")

    with pytest.raises(AsyncApiError):
        asyncio.run(_run())

    assert fake.calls == 3


def test_async_api_client_timeout_retries(monkeypatch):
    fake = FakeAsyncClient(
        exceptions=[httpx.TimeoutException("timeout")] * 3
    )

    async def _noop_sleep(_):
        return None

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: fake)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    async def _run():
        async with AsyncAPIClient(max_retries=2) as client:
            await client.make_api_call("getPrime")

    with pytest.raises(AsyncApiError):
        asyncio.run(_run())

    assert fake.calls == 3


def test_async_api_client_unsupported_method(monkeypatch):
    fake = FakeAsyncClient(responses=[_response(200)])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: fake)

    async def _run():
        async with AsyncAPIClient() as client:
            await client.make_api_call("getPrime", method="PATCH")

    with pytest.raises(ValueError):
        asyncio.run(_run())
    assert fake.calls == 0
