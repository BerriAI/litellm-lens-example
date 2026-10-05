import sys
from typing import Any, Final

import httpx
from gateway.session_context import get_session_env
from gateway_tracing.httpx import GatewayTransport
from opentelemetry import context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from providers import register_provider
from providers.base import ProviderProfile


def hermes_span_context() -> context.Context | None:
    hooks: Final = sys.modules.get("hermes_plugins.hermes_otel.hooks")
    traceparent: Final = hooks.get_current_traceparent(get_session_env("HERMES_SESSION_ID")) if hooks is not None else None
    return TraceContextTextMapPropagator().extract({"traceparent": traceparent}) if traceparent else None


class HermesSpanTransport(httpx.BaseTransport):
    def __init__(self, transport: httpx.BaseTransport) -> None:
        self._transport = transport

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        parent: Final = hermes_span_context()
        if parent is None:
            return self._transport.handle_request(request)
        token: Final = context.attach(parent)
        try:
            return self._transport.handle_request(request)
        finally:
            context.detach(token)

    def close(self) -> None:
        self._transport.close()


class LiteLLMProfile(ProviderProfile):
    def build_client_kwargs_extras(self, *, base_url: str = "", **_: Any) -> dict[str, Any]:
        transport: Final = HermesSpanTransport(GatewayTransport(base_url, httpx.HTTPTransport()))
        return {"http_client": httpx.Client(transport=transport)}


register_provider(LiteLLMProfile(name="litellm", display_name="LiteLLM", description="LiteLLM gateway"))
