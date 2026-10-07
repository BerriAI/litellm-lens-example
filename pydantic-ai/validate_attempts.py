import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LENS_TRACING_KEY']}"}
for url in filter(None, [os.environ["LENS_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

import httpx2
from gateway_tracing.httpx2 import gateway_http_client
from openai import AsyncOpenAI

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider

scenario = sys.argv[1] if len(sys.argv) > 1 else ""
if scenario not in ("retry", "response-loss"):
    raise SystemExit("Expected retry or response-loss")


class LostStream(httpx2.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        raise httpx2.ReadError("Client lost billed response")
        yield b""


def replay_headers(response: httpx2.Response) -> httpx2.Headers:
    headers = response.headers.copy()
    for name in ("content-encoding", "content-length"):
        headers.pop(name, None)
    return headers


class FaultTransport(httpx2.AsyncBaseTransport):
    def __init__(self) -> None:
        self._transport = httpx2.AsyncHTTPTransport()
        self.injected = False

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        response = await self._transport.handle_async_request(request)
        if not response.is_success:
            return response
        if scenario == "retry" and not self.injected:
            self.injected = True
            await response.aread()
            return httpx2.Response(
                503, headers=replay_headers(response), content=b"Client validation injected response loss"
            )
        if scenario == "response-loss":
            await response.aread()
            return httpx2.Response(response.status_code, headers=replay_headers(response), stream=LostStream())
        return response

    async def aclose(self) -> None:
        await self._transport.aclose()


transport = FaultTransport()
http_client = gateway_http_client(f"{os.environ['LITELLM_GATEWAY_URL']}/v1", transport=transport)
openai_client = AsyncOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    http_client=http_client,
    max_retries=1 if scenario == "retry" else 0,
)
model = OpenAIChatModel(os.environ["LITELLM_MODEL"], provider=LiteLLMProvider(openai_client=openai_client))

Agent.instrument_all()
agent = Agent(model, name="research_agent")


async def main() -> None:
    try:
        result = await agent.run("Reply with one short sentence about agent traces.")
        print(
            json.dumps(
                {"scenario": scenario, "injected": transport.injected, "result": "success", "output": result.output}
            )
        )
    except Exception as error:
        print(json.dumps({"scenario": scenario, "result": "expected client error", "error": str(error)}))
        if scenario != "response-loss":
            sys.exit(1)
    finally:
        await http_client.aclose()
        trace.get_tracer_provider().force_flush()


asyncio.run(main())
