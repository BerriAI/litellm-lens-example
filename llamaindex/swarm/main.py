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

from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

LlamaIndexInstrumentor().instrument()
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.llms.openai_like import OpenAILike

model = OpenAILike(
    model=os.environ["LITELLM_MODEL"],
    api_base=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    is_chat_model=True,
    is_function_calling_model=True,
)


async def main():
    research_agent = FunctionAgent(
        name="research_agent",
        description="Coordinates research.",
        system_prompt="Hand off to search_agent to gather facts.",
        llm=model,
        can_handoff_to=["search_agent", "writer_agent"],
    )
    search_agent = FunctionAgent(
        name="search_agent",
        description="Gathers facts.",
        system_prompt="List key facts, then hand off to writer_agent.",
        llm=model,
        can_handoff_to=["writer_agent"],
    )
    writer_agent = FunctionAgent(
        name="writer_agent",
        description="Writes the final answer.",
        system_prompt="Write a short answer from the facts.",
        llm=model,
        can_handoff_to=[],
    )
    workflow = AgentWorkflow(agents=[research_agent, search_agent, writer_agent], root_agent="research_agent")
    result = await workflow.run(user_msg="What is an agent trace?")
    print(result)


asyncio.run(main())
