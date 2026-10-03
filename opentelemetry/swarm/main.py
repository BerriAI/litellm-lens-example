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

from gateway_tracing.httpx2 import gateway_sync_http_client
from openai import OpenAI

client = OpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    http_client=gateway_sync_http_client(f"{os.environ['LITELLM_GATEWAY_URL']}/v1"),
)
tracer = trace.get_tracer(__name__)


def run_agent(name, prompt):
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("gen_ai.agent.name", name)
        span.set_attribute("openinference.span.kind", "AGENT")
        span.set_attribute("input.value", prompt)
        response = client.chat.completions.create(
            model=os.environ["LITELLM_MODEL"],
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content
        span.set_attribute("output.value", str(answer))
        return answer


with tracer.start_as_current_span("research_agent") as span:
    span.set_attribute("gen_ai.agent.name", "research_agent")
    span.set_attribute("openinference.span.kind", "AGENT")
    span.set_attribute("input.value", "What is an agent trace?")
    notes = run_agent("search_agent", "List key facts about: What is an agent trace?")
    answer = run_agent("writer_agent", f"Using these notes, answer 'What is an agent trace?':\n{notes}")
    span.set_attribute("output.value", str(answer))

print(answer)
