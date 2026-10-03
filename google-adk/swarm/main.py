import asyncio
import os

os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "SPAN_ONLY"

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LITELLM_API_KEY']}"}
for url in filter(None, [os.environ["LITELLM_GATEWAY_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner

model = LiteLlm(
    model=f"litellm_proxy/{os.environ['LITELLM_MODEL']}",
    api_base=os.environ["LITELLM_GATEWAY_URL"],
    api_key=os.environ["LITELLM_API_KEY"],
)

search_agent = Agent(
    name="search_agent",
    model=model,
    description="Gathers key facts about the question.",
    instruction="List a few key facts about the question, then transfer to writer_agent.",
)
writer_agent = Agent(
    name="writer_agent",
    model=model,
    description="Writes the final answer from the gathered facts.",
    instruction="Write a short answer to the question using the facts gathered so far.",
)
agent = Agent(
    name="research_agent",
    model=model,
    instruction="Transfer to search_agent to research the question.",
    sub_agents=[search_agent, writer_agent],
)
asyncio.run(InMemoryRunner(agent=agent).run_debug("What is an agent trace?"))
