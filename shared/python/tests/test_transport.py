import asyncio
import importlib
import os
import unittest
from collections.abc import AsyncIterator, Iterator

http = importlib.import_module(os.environ.get("GATEWAY_HTTP_MODULE", "httpx2"))
from gateway_tracing import contract
from openai import AsyncOpenAI, OpenAI
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from opentelemetry import trace

adapter = importlib.import_module(f"gateway_tracing.{http.__name__}")
gateway_http_client = adapter.gateway_http_client
gateway_sync_http_client = adapter.gateway_sync_http_client

COMPLETION = {
    "id": "response",
    "object": "chat.completion",
    "created": 1,
    "model": "test",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
}


class ControlledStream(http.AsyncByteStream):
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"first"
        if self.fail:
            raise http.ReadError("stream failed")
        yield b"last"

    async def aclose(self) -> None:
        self.closed = True


class SyncControlledStream(http.SyncByteStream):
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        yield b"first"
        if self.fail:
            raise http.ReadError("stream failed")
        yield b"last"

    def close(self) -> None:
        self.closed = True


class TransportTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exporter = InMemorySpanExporter()
        cls.provider = TracerProvider()
        cls.provider.add_span_processor(SimpleSpanProcessor(cls.exporter))
        trace.set_tracer_provider(cls.provider)

    def setUp(self) -> None:
        self.exporter.clear()

    async def test_stream_keeps_attempt_open_without_changing_context(self) -> None:
        seen = []
        stream = ControlledStream()

        async def send(request: http.Request) -> http.Response:
            seen.append(request.headers["traceparent"])
            return http.Response(200, headers={"x-litellm-call-id": "call-stream"}, stream=stream)

        async with gateway_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as client:
            with trace.get_tracer("test").start_as_current_span("model") as parent:
                async with client.stream("POST", "https://gateway.test/v1/chat/completions?secret=hidden") as response:
                    self.assertIs(trace.get_current_span(), parent)
                    self.assertEqual(self.exporter.get_finished_spans(), ())
                    self.assertEqual(await response.aread(), b"firstlast")
                self.assertIs(trace.get_current_span(), parent)
        attempt, model = self.exporter.get_finished_spans()
        self.assertEqual(attempt.parent.span_id, model.context.span_id)
        self.assertEqual(
            seen, [f"00-{model.context.trace_id:032x}-{attempt.context.span_id:016x}-{attempt.context.trace_flags:02x}"]
        )
        self.assertEqual(attempt.attributes["litellm.call_id"], "call-stream")
        self.assertTrue(attempt.attributes["litellm.gateway.attempt"])
        self.assertEqual(attempt.attributes["url.full"], "https://gateway.test/v1/chat/completions")
        self.assertTrue(stream.closed)
        self.assert_contract(attempt)

    def assert_contract(self, attempt) -> None:
        """What LiteLLM's `http_client.rs` matcher and `spend.rs` keys read from an attempt span."""
        self.assertEqual(attempt.instrumentation_scope.name, contract.SCOPE)
        self.assertEqual(attempt.name, contract.SPAN_NAME)
        self.assertIs(attempt.attributes[contract.ATTEMPT_ATTRIBUTE], True)
        self.assertEqual(attempt.attributes["http.request.method"], contract.METHOD)
        self.assertEqual(attempt.attributes["server.address"], "gateway.test")
        self.assertIn(contract.CALL_ID_ATTRIBUTE, attempt.attributes)

    async def test_requests_outside_the_contract_pass_through_untraced(self) -> None:
        seen = []

        async def send(request: http.Request) -> http.Response:
            seen.append((request.method, str(request.url), "traceparent" in request.headers))
            return http.Response(200, headers={"x-litellm-call-id": "ignored"})

        async with gateway_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as client:
            await client.get("https://gateway.test/v1/models")
            await client.post("https://other.test/v1/chat/completions")
            await client.post("https://gateway.test/health")
        self.assertEqual(
            seen,
            [
                ("GET", "https://gateway.test/v1/models", False),
                ("POST", "https://other.test/v1/chat/completions", False),
                ("POST", "https://gateway.test/health", False),
            ],
        )
        self.assertEqual(self.exporter.get_finished_spans(), ())

    def test_sync_client_follows_the_same_contract(self) -> None:
        headers = []
        stream = SyncControlledStream()

        def send(request: http.Request) -> http.Response:
            headers.append(request.headers["traceparent"])
            if len(headers) == 1:
                return http.Response(429, headers={"retry-after-ms": "1", "x-litellm-call-id": "call-failed"}, json={})
            return http.Response(200, headers={"x-litellm-call-id": "call-success"}, stream=stream)

        with gateway_sync_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as http_client:
            client = OpenAI(api_key="test", base_url="https://gateway.test/v1", http_client=http_client, max_retries=1)
            with trace.get_tracer("test").start_as_current_span("model") as parent:
                with client.chat.completions.with_streaming_response.create(
                    model="test", messages=[{"role": "user", "content": "OK"}]
                ) as response:
                    self.assertIs(trace.get_current_span(), parent)
                    self.assertEqual(len(self.exporter.get_finished_spans()), 1)
                    self.assertEqual(response.read(), b"firstlast")
        first, second, model = self.exporter.get_finished_spans()
        self.assertNotEqual(headers[0], headers[1])
        self.assertEqual(first.parent.span_id, model.context.span_id)
        self.assertEqual(second.parent.span_id, model.context.span_id)
        self.assertEqual(first.attributes["litellm.call_id"], "call-failed")
        self.assertEqual(first.status.status_code, StatusCode.ERROR)
        self.assertEqual(second.attributes["litellm.call_id"], "call-success")
        self.assertEqual(
            headers[1],
            f"00-{model.context.trace_id:032x}-{second.context.span_id:016x}-{second.context.trace_flags:02x}",
        )
        self.assertTrue(stream.closed)
        self.assert_contract(second)

    def test_sync_stream_error_and_early_close_end_the_attempt_once(self) -> None:
        for fail in (True, False):
            with self.subTest(fail=fail):
                self.exporter.clear()
                stream = SyncControlledStream(fail=fail)

                def send(request: http.Request, stream: SyncControlledStream = stream) -> http.Response:
                    return http.Response(200, stream=stream)

                with gateway_sync_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as client:
                    if fail:
                        with self.assertRaises(http.ReadError):
                            with client.stream("POST", "https://gateway.test/v1/chat/completions") as response:
                                response.read()
                    else:
                        with client.stream("POST", "https://gateway.test/v1/chat/completions"):
                            self.assertEqual(self.exporter.get_finished_spans(), ())
                (span,) = self.exporter.get_finished_spans()
                self.assertEqual(span.attributes.get("error.type"), "ReadError" if fail else None)
                self.assertTrue(stream.closed)

    async def test_early_close_ends_attempt_without_reading_the_whole_body(self) -> None:
        stream = ControlledStream()

        async def send(request: http.Request) -> http.Response:
            return http.Response(200, stream=stream)

        async with gateway_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as client:
            async with client.stream("POST", "https://gateway.test/v1/chat/completions"):
                self.assertEqual(self.exporter.get_finished_spans(), ())
        self.assertEqual(len(self.exporter.get_finished_spans()), 1)
        self.assertTrue(stream.closed)

    async def test_stream_error_ends_once_and_preserves_exception(self) -> None:
        stream = ControlledStream(fail=True)

        async def send(request: http.Request) -> http.Response:
            return http.Response(200, stream=stream)

        async with gateway_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as client:
            with self.assertRaises(http.ReadError):
                async with client.stream("POST", "https://gateway.test/v1/chat/completions") as response:
                    await response.aread()
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].status.status_code, StatusCode.ERROR)
        self.assertEqual(spans[0].attributes["error.type"], "ReadError")
        self.assertTrue(stream.closed)

    async def test_sdk_retry_has_distinct_attempts_with_shared_model_parent(self) -> None:
        headers = []

        async def send(request: http.Request) -> http.Response:
            headers.append(request.headers["traceparent"])
            if len(headers) == 1:
                return http.Response(
                    429,
                    headers={"retry-after-ms": "1", "x-litellm-call-id": "call-failed"},
                    json={"error": {"message": "retry"}},
                )
            return http.Response(200, headers={"x-litellm-call-id": "call-success"}, json=COMPLETION)

        async with gateway_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as http_client:
            client = AsyncOpenAI(
                api_key="test", base_url="https://gateway.test/v1", http_client=http_client, max_retries=1
            )
            with trace.get_tracer("test").start_as_current_span("model"):
                response = await client.chat.completions.create(
                    model="test", messages=[{"role": "user", "content": "OK"}]
                )
                self.assertEqual(response.choices[0].message.content, "OK")
        first, second, model = self.exporter.get_finished_spans()
        self.assertNotEqual(headers[0], headers[1])
        self.assertEqual(first.parent.span_id, model.context.span_id)
        self.assertEqual(second.parent.span_id, model.context.span_id)
        self.assertEqual(first.attributes["litellm.call_id"], "call-failed")
        self.assertEqual(second.attributes["litellm.call_id"], "call-success")

    async def test_cancelled_send_ends_attempt_and_preserves_cancellation(self) -> None:
        async def send(request: http.Request) -> http.Response:
            raise asyncio.CancelledError()

        async with gateway_http_client("https://gateway.test/v1", transport=http.MockTransport(send)) as client:
            with self.assertRaises(asyncio.CancelledError):
                await client.post("https://gateway.test/v1/chat/completions")
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].attributes["error.type"], "CancelledError")


if __name__ == "__main__":
    unittest.main()
