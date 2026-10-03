import os

os.environ["OTEL_SEMCONV_STABILITY_OPT_IN"] = "gen_ai_latest_experimental,gen_ai_span_attributes_only"

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LITELLM_API_KEY']}"}
for url in filter(None, [os.environ["LITELLM_GATEWAY_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

from gateway_tracing.httpx import gateway_http_client
from openai import AsyncOpenAI
from strands import Agent
from strands.models.openai import OpenAIModel

client = AsyncOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    http_client=gateway_http_client(f"{os.environ['LITELLM_GATEWAY_URL']}/v1"),
)
model = OpenAIModel(client=client, model_id=os.environ["LITELLM_MODEL"])

agent = Agent(name="research_agent", model=model, callback_handler=None)
print(agent("What is an agent trace?"))
