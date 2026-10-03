import http.client
import unittest
from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import SimpleQueue
from threading import Thread
from typing import Final
from urllib.parse import urlsplit

from gateway import handler_type


@dataclass(frozen=True, slots=True)
class Request:
    path: str
    body: bytes
    authorization: str | None


@contextmanager
def server(handler: type[BaseHTTPRequestHandler]) -> Generator[ThreadingHTTPServer]:
    instance: Final = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread: Final = Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join()


def upstream_handler(
    requests: SimpleQueue[Request], body: bytes, content_type: str, identity: str
) -> type[BaseHTTPRequestHandler]:
    class Upstream(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            requests.put(
                Request(
                    self.path,
                    self.rfile.read(int(self.headers["Content-Length"])),
                    self.headers.get("Authorization"),
                )
            )
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("request-id", identity)
            self.end_headers()
            self.wfile.write(body)

    return Upstream


class GatewayTest(unittest.TestCase):
    def test_message_id_links_spend_without_changing_response_bytes(self) -> None:
        cases: Final = (
            (b'{"id":"msg_fixture","content":[]}', "application/json", "msg_fixture"),
            (
                b'event: message_start\ndata: {"message":{"id":"msg_fixture"}}\n\n'
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
                "text/event-stream",
                "msg_fixture",
            ),
            (
                b'{"error":{"message":"rejected"}}',
                "application/json",
                "original-request",
            ),
        )
        for body, content_type, expected in cases:
            with self.subTest(content_type=content_type, body=body):
                self.assert_message_preserved(body, content_type, expected)

    def assert_message_preserved(self, body: bytes, content_type: str, expected: str) -> None:
        requests: Final[SimpleQueue[Request]] = SimpleQueue()
        with server(upstream_handler(requests, body, content_type, "original-request")) as upstream:
            address: Final = urlsplit(f"http://127.0.0.1:{upstream.server_port}")
            with server(handler_type(address, None)) as gateway:
                with closing(http.client.HTTPConnection("127.0.0.1", gateway.server_port)) as client:
                    client.request(
                        "POST",
                        "/v1/messages",
                        b"{}",
                        {"Authorization": "Bearer fixture-key"},
                    )
                    response: Final = client.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader("request-id"), expected)
                    self.assertEqual(response.read(), body)
            self.assertEqual(
                requests.get_nowait(),
                Request("/v1/messages", b"{}", "Bearer fixture-key"),
            )
            self.assertTrue(requests.empty())

    def test_chunked_export_reaches_proxy_and_recorder_once(self) -> None:
        proxy_requests: Final[SimpleQueue[Request]] = SimpleQueue()
        recorder_requests: Final[SimpleQueue[Request]] = SimpleQueue()
        with server(upstream_handler(proxy_requests, b"{}", "application/json", "proxy-id")) as proxy:
            with server(upstream_handler(recorder_requests, b"{}", "application/json", "recorder-id")) as recorder:
                proxy_url: Final = urlsplit(f"http://127.0.0.1:{proxy.server_port}")
                recorder_url: Final = urlsplit(f"http://127.0.0.1:{recorder.server_port}")
                with server(handler_type(proxy_url, recorder_url)) as gateway:
                    with closing(http.client.HTTPConnection("127.0.0.1", gateway.server_port)) as client:
                        client.request(
                            "POST",
                            "/v1/traces?format=json",
                            iter((b'{"resource', b'Spans":[]}')),
                            {"Authorization": "Bearer fixture-key"},
                            encode_chunked=True,
                        )
                        response: Final = client.getresponse()
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read(), b"{}")
                expected: Final = Request(
                    "/v1/traces?format=json",
                    b'{"resourceSpans":[]}',
                    "Bearer fixture-key",
                )
                self.assertEqual(proxy_requests.get_nowait(), expected)
                self.assertEqual(recorder_requests.get_nowait(), expected)
                self.assertTrue(proxy_requests.empty())
                self.assertTrue(recorder_requests.empty())


if __name__ == "__main__":
    unittest.main()
