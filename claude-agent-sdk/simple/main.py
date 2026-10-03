import asyncio
import os

os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "gen_ai.agent.name=research_agent"

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LITELLM_API_KEY']}"}
for url in filter(None, [os.environ["LITELLM_GATEWAY_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

options = ClaudeAgentOptions(
    model=os.environ["LITELLM_MODEL"],
    env={
        "ANTHROPIC_BASE_URL": os.environ["LITELLM_GATEWAY_URL"],
        "ANTHROPIC_AUTH_TOKEN": os.environ["LITELLM_API_KEY"],
        "OTEL_EXPORTER_OTLP_HEADERS": f"Authorization=Bearer {os.environ['LITELLM_API_KEY']}",
        "OTEL_LOG_USER_PROMPTS": "1",
        "ENABLE_BETA_TRACING_DETAILED": "1",
        "BETA_TRACING_ENDPOINT": os.environ["LITELLM_GATEWAY_URL"],
    },
)


async def main():
    async for message in query(prompt="What is an agent trace?", options=options):
        if isinstance(message, ResultMessage):
            print(message.result)


asyncio.run(main())
