import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LENS_TRACING_KEY']}"}
for url in filter(None, [os.environ["LENS_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    model=os.environ["LITELLM_MODEL"],
)

search_agent = create_agent(name="search_agent", model=model, system_prompt="Find key facts about the topic.")
writer_agent = create_agent(name="writer_agent", model=model, system_prompt="Write a short answer from the facts.")


@tool
def search(query: str) -> str:
    """Find key facts about a topic."""
    return search_agent.invoke({"messages": [{"role": "user", "content": query}]})["messages"][-1].content


@tool
def write(facts: str) -> str:
    """Write a short answer from facts."""
    return writer_agent.invoke({"messages": [{"role": "user", "content": facts}]})["messages"][-1].content


agent = create_agent(
    name="research_agent",
    model=model,
    tools=[search, write],
    system_prompt="Use search, then write, then return the written answer.",
)
result = agent.invoke({"messages": [{"role": "user", "content": "What is an agent trace?"}]})
print(result["messages"][-1].content)
