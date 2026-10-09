import os

from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

trace.set_tracer_provider(TracerProvider())
OpenAIAgentsInstrumentor().instrument(exclusive_processor=True)

headers = {"Authorization": f"Bearer {os.environ['LENS_TRACING_KEY']}"}
for url in filter(None, [os.environ["LENS_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

from agents import Agent, OpenAIResponsesModel, RunConfig, Runner
from gateway_tracing.httpx2 import gateway_http_client
from openai import AsyncOpenAI

gateway_url = os.environ.get("LITELLM_GATEWAY_URL")
client = (
    AsyncOpenAI(
        base_url=f"{gateway_url.rstrip('/')}/v1",
        api_key=os.environ["LITELLM_API_KEY"],
        http_client=gateway_http_client(f"{gateway_url.rstrip('/')}/v1"),
    )
    if gateway_url
    else AsyncOpenAI()
)
model = OpenAIResponsesModel(
    model=os.environ["LITELLM_MODEL" if gateway_url else "OPENAI_MODEL"],
    openai_client=client,
)

search_agent = Agent(name="search_agent", instructions="Find key facts about the topic.", model=model)
writer_agent = Agent(name="writer_agent", instructions="Write a short answer from the given facts.", model=model)
agent = Agent(
    name="research_agent",
    instructions="Use search_agent to gather facts, then writer_agent to write the answer.",
    model=model,
    tools=[
        search_agent.as_tool("search_agent", "Find key facts about a topic."),
        writer_agent.as_tool("writer_agent", "Write a short answer from facts."),
    ],
)
result = Runner.run_sync(agent, "What is an agent trace?", run_config=RunConfig(workflow_name="research_workflow"))
print(result.final_output)
