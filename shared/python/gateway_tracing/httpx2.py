import httpx2 as http

from ._transport import adapters

_adapters = adapters(http)
AsyncGatewayTransport = _adapters.AsyncGatewayTransport
GatewayTransport = _adapters.GatewayTransport
gateway_http_client = _adapters.gateway_http_client
gateway_sync_http_client = _adapters.gateway_sync_http_client

__all__ = ["AsyncGatewayTransport", "GatewayTransport", "gateway_http_client", "gateway_sync_http_client"]
