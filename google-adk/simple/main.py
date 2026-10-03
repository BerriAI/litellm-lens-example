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

agent = Agent(name="research_agent", model=model)
asyncio.run(InMemoryRunner(agent=agent, app_name="research_app").run_debug("What is an agent trace?"))
