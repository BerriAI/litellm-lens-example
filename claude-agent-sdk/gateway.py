import http.client
import os
from collections.abc import Iterator
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final
from urllib.parse import SplitResult, urlsplit

from pydantic import JsonValue, TypeAdapter

JSON: Final = TypeAdapter(dict[str, JsonValue])
HOP_HEADERS: Final = frozenset({"host", "connection", "transfer-encoding", "content-length", "accept-encoding"})


def response_id(body: bytes) -> str | None:
    payload: Final = body.removeprefix(b"data: ").strip()
    try:
        event: Final = JSON.validate_json(payload)
    except ValueError:
        return None
    message: Final = event.get("message", event)
    if not isinstance(message, dict):
        return None
    identity: Final = message.get("id")
    return identity if isinstance(identity, str) and identity else None


def stream_prefix(response: http.client.HTTPResponse) -> Iterator[bytes]:
    for line in response:
        yield line
        if response_id(line) is not None:
            return


def chunks(handler: BaseHTTPRequestHandler) -> Iterator[bytes]:
    for size in iter(lambda: int(handler.rfile.readline().strip(), 16), 0):
        yield handler.rfile.read(size)
        handler.rfile.readline()
    handler.rfile.readline()


def handler_type(gateway: SplitResult, recorder_url: SplitResult | None) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body: Final = (
                b"".join(chunks(self))
                if self.headers.get("Transfer-Encoding") == "chunked"
                else self.rfile.read(int(self.headers.get("Content-Length", 0)))
            )
            headers: Final = {key: value for key, value in self.headers.items() if key.lower() not in HOP_HEADERS}
            if self.path.split("?")[0] == "/v1/traces" and recorder_url is not None:
                with closing(
                    http.client.HTTPConnection(
                        recorder_url.hostname or "localhost",
                        recorder_url.port,
                        timeout=30,
                    )
                ) as recorder:
                    recorder.request(
                        "POST",
                        recorder_url.path.rstrip("/") + self.path,
                        body=body,
                        headers=headers,
                    )
                    recorded: Final = recorder.getresponse()
                    recorded.read()
                    if recorded.status != 200:
                        self.send_error(502, "Trace recorder rejected the export")
                        return
            connection: Final = http.client.HTTPSConnection if gateway.scheme == "https" else http.client.HTTPConnection
            with closing(connection(gateway.hostname or "localhost", gateway.port, timeout=120)) as upstream:
                upstream.request(
                    "POST",
                    gateway.path.rstrip("/") + self.path,
                    body=body,
                    headers=headers,
                )
                response: Final = upstream.getresponse()
                streaming: Final = "text/event-stream" in (response.getheader("Content-Type") or "")
                prefix: Final = tuple(stream_prefix(response)) if streaming else (response.read(),)
                identity: Final = next(
                    (candidate for part in prefix if (candidate := response_id(part)) is not None),
                    None,
                )
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in HOP_HEADERS and key.lower() != "request-id":
                        self.send_header(key, value)
                request_id: Final = identity or response.getheader("request-id")
                if request_id is not None:
                    self.send_header("request-id", request_id)
                self.end_headers()
                for part in prefix:
                    self.wfile.write(part)
                self.wfile.flush()
                if streaming:
                    for chunk in iter(lambda: response.read1(65536), b""):
                        self.wfile.write(chunk)
                        self.wfile.flush()

    return Handler


if __name__ == "__main__":
    gateway: Final = urlsplit(os.environ["LITELLM_GATEWAY_URL"])
    recorder_url: Final = (
        urlsplit(os.environ["MOCK_LITELLM_GATEWAY_URL"]) if os.environ.get("MOCK_LITELLM_GATEWAY_URL") else None
    )
    port: Final = int(os.environ.get("CLAUDE_GATEWAY_PORT", "4319"))
    ThreadingHTTPServer(("127.0.0.1", port), handler_type(gateway, recorder_url)).serve_forever()
