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

from agents import Agent, OpenAIChatCompletionsModel, Runner
from openai import AsyncOpenAI

model = OpenAIChatCompletionsModel(
    model=os.environ["LITELLM_MODEL"],
    openai_client=AsyncOpenAI(
        base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
        api_key=os.environ["LITELLM_API_KEY"],
    ),
)

agent = Agent(name="research_agent", model=model)
result = Runner.run_sync(agent, "What is an agent trace?")
print(result.final_output)
