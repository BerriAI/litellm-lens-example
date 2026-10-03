import asyncio
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LITELLM_API_KEY']}"}
for url in filter(None, [os.environ["LITELLM_GATEWAY_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

import ai
from ai.experimental_telemetry import otel
from ai.providers.openai import OpenAIChatCompletionsProtocol
from gateway_tracing.httpx2 import gateway_http_client
from openai import AsyncOpenAI

ai.experimental_telemetry.register(otel.OtelAdapter(capture_content=True))

http_client = gateway_http_client(f"{os.environ['LITELLM_GATEWAY_URL']}/v1")
client = AsyncOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    http_client=http_client,
)
model = ai.Model(
    id=os.environ["LITELLM_MODEL"],
    provider=ai.get_provider("openai", client=client),
    protocol=OpenAIChatCompletionsProtocol(),
)


class search_agent(ai.Agent):  # noqa: N801 - the class name becomes gen_ai.agent.name
    pass


class writer_agent(ai.Agent):  # noqa: N801
    pass


@ai.tool
async def search(query: str) -> ai.SubAgentTool:
    """Find key facts about the topic."""
    messages = [ai.system_message("Find key facts about the topic."), ai.user_message(query)]
    async with search_agent().run(model, messages) as stream:
        async for event in stream:
            yield event


@ai.tool
async def write(facts: str) -> ai.SubAgentTool:
    """Write a short answer from the given facts."""
    messages = [ai.system_message("Write a short answer from the given facts."), ai.user_message(facts)]
    async with writer_agent().run(model, messages) as stream:
        async for event in stream:
            yield event


class research_agent(ai.Agent):  # noqa: N801
    TOOLS = [search, write]


async def main() -> None:
    messages = [
        ai.system_message("Call search first, then write with the facts, and return the written answer."),
        ai.user_message("What is an agent trace?"),
    ]
    try:
        async with research_agent().run(model, messages) as stream:
            async for _ in stream:
                pass
        print(stream.output)
    finally:
        await http_client.aclose()
        trace.get_tracer_provider().force_flush()


asyncio.run(main())
