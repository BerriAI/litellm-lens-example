import asyncio
import unittest
import importlib
import os
from collections.abc import AsyncIterator

http = importlib.import_module(os.environ.get("GATEWAY_HTTP_MODULE", "httpx2"))
from openai import AsyncOpenAI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

gateway_http_client = importlib.import_module(f"gateway_tracing.{http.__name__}").gateway_http_client


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
            return http.Response(
                200,
                headers={"x-litellm-call-id": "call-success"},
                json={
                    "id": "response",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "test",
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}
                    ],
                },
            )

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
