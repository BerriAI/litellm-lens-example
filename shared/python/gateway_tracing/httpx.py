from collections.abc import AsyncIterator
from typing import Final

import httpx as http

from ._attempt import Attempt, begin


class GatewayStream(http.AsyncByteStream):
    def __init__(self, stream: http.AsyncByteStream, attempt: Attempt) -> None:
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


class GatewayTransport(http.AsyncBaseTransport):
    def __init__(self, base_url: str, transport: http.AsyncBaseTransport) -> None:
        self._base_url = base_url
        self._transport = transport

    async def handle_async_request(self, request: http.Request) -> http.Response:
        attempt: Final = begin(self._base_url, request.method, str(request.url))
        if attempt is None:
            return await self._transport.handle_async_request(request)
        request.headers.update(attempt.headers())
        try:
            response: Final = await self._transport.handle_async_request(request)
        except BaseException as error:
            attempt.finish(error)
            raise
        attempt.response(response.status_code, response.headers.get("x-litellm-call-id"))
        return http.Response(
            response.status_code,
            headers=response.headers,
            stream=GatewayStream(response.stream, attempt),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self._transport.aclose()


def gateway_http_client(base_url: str, *, transport: http.AsyncBaseTransport | None = None) -> http.AsyncClient:
    underlying: Final = transport if transport is not None else http.AsyncHTTPTransport()
    return http.AsyncClient(transport=GatewayTransport(base_url, underlying), timeout=60.0)
