"""One transport implementation for both `httpx` and `httpx2`, which share the same transport and stream API."""

from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Final

from . import contract
from ._attempt import Attempt, begin


@dataclass(frozen=True, slots=True)
class Adapters:
    AsyncGatewayTransport: type[Any]
    GatewayTransport: type[Any]
    gateway_http_client: Callable[..., Any]
    gateway_sync_http_client: Callable[..., Any]


def adapters(http: ModuleType) -> Adapters:
    class AsyncGatewayStream(http.AsyncByteStream):
        def __init__(self, stream: Any, attempt: Attempt) -> None:
            self._stream = stream
            self._attempt = attempt

        async def __aiter__(self) -> AsyncIterator[bytes]:
            try:
                async for chunk in self._stream:
                    yield chunk
            except BaseException as error:
                self._attempt.finish(error)
                raise
            finally:
                self._attempt.finish()

        async def aclose(self) -> None:
            try:
                await self._stream.aclose()
            except BaseException as error:
                self._attempt.finish(error)
                raise
            finally:
                self._attempt.finish()

    class GatewayStream(http.SyncByteStream):
        def __init__(self, stream: Any, attempt: Attempt) -> None:
            self._stream = stream
            self._attempt = attempt

        def __iter__(self) -> Iterator[bytes]:
            try:
                yield from self._stream
            except BaseException as error:
                self._attempt.finish(error)
                raise
            finally:
                self._attempt.finish()

        def close(self) -> None:
            try:
                self._stream.close()
            except BaseException as error:
                self._attempt.finish(error)
                raise
            finally:
                self._attempt.finish()

    def respond(attempt: Attempt, response: Any, stream: Any) -> Any:
        attempt.response(response.status_code, response.headers.get(contract.CALL_ID_HEADER))
        return http.Response(
            response.status_code,
            headers=response.headers,
            stream=stream,
            extensions=response.extensions,
        )

    class AsyncGatewayTransport(http.AsyncBaseTransport):
        def __init__(self, base_url: str, transport: Any) -> None:
            self._base_url = base_url
            self._transport = transport

        async def handle_async_request(self, request: Any) -> Any:
            attempt: Final = begin(self._base_url, request.method, str(request.url))
            if attempt is None:
                return await self._transport.handle_async_request(request)
            request.headers.update(attempt.headers())
            try:
                response: Final = await self._transport.handle_async_request(request)
            except BaseException as error:
                attempt.finish(error)
                raise
            return respond(attempt, response, AsyncGatewayStream(response.stream, attempt))

        async def aclose(self) -> None:
            await self._transport.aclose()

    class GatewayTransport(http.BaseTransport):
        def __init__(self, base_url: str, transport: Any) -> None:
            self._base_url = base_url
            self._transport = transport

        def handle_request(self, request: Any) -> Any:
            attempt: Final = begin(self._base_url, request.method, str(request.url))
            if attempt is None:
                return self._transport.handle_request(request)
            request.headers.update(attempt.headers())
            try:
                response: Final = self._transport.handle_request(request)
            except BaseException as error:
                attempt.finish(error)
                raise
            return respond(attempt, response, GatewayStream(response.stream, attempt))

        def close(self) -> None:
            self._transport.close()

    def gateway_http_client(base_url: str, *, transport: Any = None) -> Any:
        underlying: Final = transport if transport is not None else http.AsyncHTTPTransport()
        return http.AsyncClient(transport=AsyncGatewayTransport(base_url, underlying), timeout=60.0)

    def gateway_sync_http_client(base_url: str, *, transport: Any = None) -> Any:
        underlying: Final = transport if transport is not None else http.HTTPTransport()
        return http.Client(transport=GatewayTransport(base_url, underlying), timeout=60.0)

    return Adapters(AsyncGatewayTransport, GatewayTransport, gateway_http_client, gateway_sync_http_client)
