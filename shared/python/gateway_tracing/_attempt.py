from dataclasses import dataclass
from typing import Final
from urllib.parse import urlsplit, urlunsplit

from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


@dataclass(slots=True)
class Attempt:
    span: Span
    ended: bool = False

    def response(self, status: int, call_id: str | None) -> None:
        self.span.set_attribute("http.response.status_code", status)
        if call_id:
            self.span.set_attribute("litellm.call_id", call_id)
        if status >= 400:
            self.span.set_status(Status(StatusCode.ERROR))

    def finish(self, error: BaseException | None = None) -> None:
        if self.ended:
            return
        self.ended = True
        if error is not None:
            self.span.set_attribute("error.type", type(error).__name__)
            self.span.set_status(Status(StatusCode.ERROR))
        self.span.end()

    def headers(self) -> dict[str, str]:
        carrier: Final[dict[str, str]] = {}
        TraceContextTextMapPropagator().inject(carrier, context=trace.set_span_in_context(self.span))
        return carrier


def begin(base_url: str, method: str, url: str) -> Attempt | None:
    base: Final = urlsplit(base_url)
    target: Final = urlsplit(url)
    if method != "POST" or (base.scheme, base.hostname, base.port) != (target.scheme, target.hostname, target.port):
        return None
    if not target.path.startswith(base.path.rstrip("/") + "/"):
        return None
    hostname: Final = target.hostname or ""
    authority: Final = f"[{hostname}]" if ":" in hostname else hostname
    netloc: Final = f"{authority}:{target.port}" if target.port is not None else authority
    sanitized: Final = urlunsplit((target.scheme, netloc, target.path, "", ""))
    span: Final = trace.get_tracer("litellm.gateway.client").start_span(
        "gateway.request",
        kind=SpanKind.CLIENT,
        attributes={
            "litellm.gateway.attempt": True,
            "http.request.method": method,
            "url.full": sanitized,
            "server.address": hostname,
        },
    )
    return Attempt(span)
