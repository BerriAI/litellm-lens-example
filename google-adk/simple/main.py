import asyncio
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

from gateway_tracing.httpx import gateway_http_client
from google.adk.agents import Agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from openai import AsyncOpenAI


client = AsyncOpenAI(
    api_key=os.environ["LITELLM_API_KEY"],
    base_url=f"{os.environ['LITELLM_GATEWAY_URL'].rstrip('/')}/v1",
    http_client=gateway_http_client(os.environ["LITELLM_GATEWAY_URL"]),
)
model = LiteLlm(
    model=f"openai/{os.environ['LITELLM_MODEL']}",
    client=client,
    api_base=f"{os.environ['LITELLM_GATEWAY_URL'].rstrip('/')}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
)

agent = Agent(name="research_agent", model=model)
run_config = RunConfig(
    streaming_mode=StreamingMode.SSE if os.environ.get("LITELLM_STREAM") == "1" else StreamingMode.NONE
)
asyncio.run(
    InMemoryRunner(agent=agent, app_name="research_app").run_debug("What is an agent trace?", run_config=run_config)
)
