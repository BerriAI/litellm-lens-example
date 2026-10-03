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

from agents import Agent, OpenAIResponsesModel, RunConfig, Runner
from openai import AsyncOpenAI

model = OpenAIResponsesModel(
    model=os.environ["LITELLM_MODEL"],
    openai_client=AsyncOpenAI(
        base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
        api_key=os.environ["LITELLM_API_KEY"],
    ),
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
