import asyncio
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

import litellm
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools.agent_tool import AgentTool
from litellm.integrations.custom_logger import CustomLogger


class ResponseIdLogger(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        trace.get_current_span().set_attribute("gen_ai.response.id", response_obj.id)


litellm.callbacks = [ResponseIdLogger()]
model = LiteLlm(
    model=f"litellm_proxy/{os.environ['LITELLM_MODEL']}",
    api_base=os.environ["LITELLM_GATEWAY_URL"],
    api_key=os.environ["LITELLM_API_KEY"],
)

search_agent = Agent(
    name="search_agent",
    model=model,
    description="Gathers key facts about the question.",
    instruction="List a few key facts about the question.",
)
writer_agent = Agent(
    name="writer_agent",
    model=model,
    description="Writes the final answer from the gathered facts.",
    instruction="Write a short answer to the question from the given facts.",
)
agent = Agent(
    name="research_agent",
    model=model,
    instruction="Use search_agent to gather facts, then writer_agent to write the answer from them.",
    tools=[AgentTool(search_agent), AgentTool(writer_agent)],
)
asyncio.run(InMemoryRunner(agent=agent, app_name="research_app").run_debug("What is an agent trace?"))
