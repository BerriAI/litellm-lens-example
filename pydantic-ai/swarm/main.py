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

from gateway_tracing.httpx2 import gateway_http_client

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider

http_client = gateway_http_client(f"{os.environ['LITELLM_GATEWAY_URL']}/v1")
model = OpenAIChatModel(
    os.environ["LITELLM_MODEL"],
    provider=LiteLLMProvider(
        api_base=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
        api_key=os.environ["LITELLM_API_KEY"],
        http_client=http_client,
    ),
)

Agent.instrument_all()
search_agent = Agent(model, name="search_agent", instructions="Find key facts about the topic.")
writer_agent = Agent(model, name="writer_agent", instructions="Write a short answer from the given facts.")
agent = Agent(
    model,
    name="research_agent",
    instructions="Call search first, then write with the facts, and return the written answer.",
)


@agent.tool
async def search(ctx: RunContext, query: str) -> str:
    return (await search_agent.run(query, usage=ctx.usage)).output


@agent.tool
async def write(ctx: RunContext, facts: str) -> str:
    return (await writer_agent.run(facts, usage=ctx.usage)).output


async def main() -> None:
    try:
        if os.environ.get("LITELLM_STREAM") == "1":
            async with agent.run_stream("What is an agent trace?") as result:
                print(await result.get_output())
        else:
            print((await agent.run("What is an agent trace?")).output)
    finally:
        await http_client.aclose()
        trace.get_tracer_provider().force_flush()


asyncio.run(main())
