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

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    model=os.environ["LITELLM_MODEL"],
    use_responses_api=True,
)

subagents = [
    {"name": "search_agent", "description": "Finds facts about the topic.", "system_prompt": "Return key facts about the topic."},
    {"name": "writer_agent", "description": "Writes the final answer from facts.", "system_prompt": "Write a short answer from the given facts."},
]
agent = create_deep_agent(
    name="research_agent",
    model=model,
    tools=[],
    subagents=subagents,
    system_prompt="Use the task tool to call search_agent, then writer_agent with its facts, and return the writer's answer.",
)
result = agent.invoke({"messages": [{"role": "user", "content": "What is an agent trace?"}]})
print(result["messages"][-1].text)
