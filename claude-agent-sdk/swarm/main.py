import asyncio
import os

os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "gen_ai.agent.name=research_agent"

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LENS_TRACING_KEY']}"}
for url in filter(None, [os.environ["LENS_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ResultMessage, query

options = ClaudeAgentOptions(
    model=os.environ["LITELLM_MODEL"],
    tools=["Agent"],
    permission_mode="bypassPermissions",
    setting_sources=[],
    system_prompt="Answer by delegating: first ask search_agent for facts, then ask writer_agent to write the final answer from them.",
    agents={
        "search_agent": AgentDefinition(
            description="Gathers key facts about a topic.",
            prompt="List the key facts about the topic in a few bullet points.",
            tools=[],
            model="inherit",
        ),
        "writer_agent": AgentDefinition(
            description="Writes a short answer from given facts.",
            prompt="Write a short, clear answer from the given facts.",
            tools=[],
            model="inherit",
        ),
    },
    env={
        "ANTHROPIC_BASE_URL": os.environ["LITELLM_GATEWAY_URL"],
        "ANTHROPIC_AUTH_TOKEN": os.environ["LITELLM_API_KEY"],
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "OTEL_EXPORTER_OTLP_HEADERS": f"Authorization=Bearer {os.environ['LENS_TRACING_KEY']}",
        "OTEL_LOG_USER_PROMPTS": "1",
        "OTEL_LOG_TOOL_DETAILS": "1",
        "ENABLE_BETA_TRACING_DETAILED": "1",
        "BETA_TRACING_ENDPOINT": os.environ["LENS_URL"],
        "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
    },
)


async def main():
    async for message in query(prompt="What is an agent trace?", options=options):
        if isinstance(message, ResultMessage):
            print(message.result)


asyncio.run(main())
