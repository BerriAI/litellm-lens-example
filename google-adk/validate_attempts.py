import asyncio
import json
import os
import sys

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LENS_TRACING_KEY']}"}
for url in filter(None, [os.environ["LENS_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

import httpx
from gateway_tracing.httpx import gateway_http_client
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from openai import AsyncOpenAI

scenario = sys.argv[1] if len(sys.argv) > 1 else ""
if scenario not in ("retry", "response-loss"):
    raise SystemExit("Expected retry or response-loss")


class LostStream(httpx.AsyncByteStream):
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise RuntimeError("Client lost billed response")


class FaultTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self._transport = httpx.AsyncHTTPTransport()
        self.injected = False

    async def handle_async_request(self, request):
        response = await self._transport.handle_async_request(request)
        if response.status_code >= 400:
            return response
        if scenario == "retry" and not self.injected:
            self.injected = True
            await response.aread()
            await response.aclose()
            headers = response.headers.copy()
            for key in ("content-encoding", "content-length"):
                headers.pop(key, None)
            return httpx.Response(503, headers=headers, content=b"Client validation injected response loss")
        if scenario == "response-loss":
            await response.aread()
            await response.aclose()
            return httpx.Response(response.status_code, headers=response.headers, stream=LostStream())
        return response

    async def aclose(self):
        await self._transport.aclose()


transport = FaultTransport()
max_retries = 1 if scenario == "retry" else 0
client = AsyncOpenAI(
    api_key=os.environ["LITELLM_API_KEY"],
    base_url=f"{os.environ['LITELLM_GATEWAY_URL'].rstrip('/')}/v1",
    http_client=gateway_http_client(os.environ["LITELLM_GATEWAY_URL"], transport=transport),
    max_retries=max_retries,
)
model = LiteLlm(
    model=f"openai/{os.environ['LITELLM_MODEL']}",
    client=client,
    api_base=f"{os.environ['LITELLM_GATEWAY_URL'].rstrip('/')}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    max_retries=max_retries,
)
agent = Agent(name="research_agent", model=model)
runner = InMemoryRunner(agent=agent, app_name="research_app")


async def main():
    try:
        await runner.run_debug("Reply with one short sentence about agent traces.")
        print(json.dumps({"scenario": scenario, "injected": transport.injected, "result": "success"}))
    except Exception as error:
        print(json.dumps({"scenario": scenario, "result": "expected client error", "error": str(error)}))
        if scenario != "response-loss":
            sys.exit(1)


asyncio.run(main())
