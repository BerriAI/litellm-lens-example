import json
import os
import sys

os.environ["OTEL_SEMCONV_STABILITY_OPT_IN"] = "gen_ai_latest_experimental,gen_ai_span_attributes_only"

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LITELLM_API_KEY']}"}
for url in filter(None, [os.environ["LITELLM_GATEWAY_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

import httpx
from gateway_tracing.httpx import gateway_http_client
from openai import AsyncOpenAI
from strands import Agent
from strands.models.openai import OpenAIModel

scenario = sys.argv[1] if len(sys.argv) > 1 else ""
if scenario not in ("retry", "response-loss"):
    raise SystemExit("Expected retry or response-loss")


class LostStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        raise httpx.ReadError("Client lost billed response")
        yield b""


class FaultTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.transport = httpx.AsyncHTTPTransport()
        self.injected = False

    async def handle_async_request(self, request):
        response = await self.transport.handle_async_request(request)
        if response.status_code >= 400 or (scenario == "retry" and self.injected):
            return response
        await response.aread()
        if scenario == "retry":
            self.injected = True
            return httpx.Response(
                503,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ("content-encoding", "content-length")},
                content=b"Client validation injected response loss",
                extensions=response.extensions,
            )
        return httpx.Response(
            response.status_code, headers=response.headers, stream=LostStream(), extensions=response.extensions
        )

    async def aclose(self):
        await self.transport.aclose()


transport = FaultTransport()
client = AsyncOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    max_retries=1 if scenario == "retry" else 0,
    http_client=gateway_http_client(f"{os.environ['LITELLM_GATEWAY_URL']}/v1", transport=transport),
)
model = OpenAIModel(client=client, model_id=os.environ["LITELLM_MODEL"])
agent = Agent(name="research_agent", model=model, callback_handler=None)

try:
    agent("Reply with one short sentence about agent traces.")
    print(json.dumps({"scenario": scenario, "injected": transport.injected, "result": "success"}))
except Exception as error:
    print(json.dumps({"scenario": scenario, "result": "expected client error", "error": str(error)}))
    if scenario != "response-loss":
        sys.exit(1)
