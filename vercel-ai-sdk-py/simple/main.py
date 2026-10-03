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

import ai
from ai import experimental_telemetry as telemetry
from ai.experimental_telemetry import otel
from ai.providers.openai import OpenAIChatCompletionsProtocol
from gateway_tracing.httpx2 import gateway_http_client
from openai import AsyncOpenAI


class GatewayOtelAdapter(otel.OtelAdapter):
    """Nest `gateway.request` spans under the model call span.

    ai keeps its model call span out of the current context because the span stays open while the loop dispatches
    tools. Making it current, and parenting framework spans explicitly, keeps the framework tree intact while the HTTP
    client's spans attach to the model call instead of the loop turn.
    """

    def _parent_context(self, span):
        if span.parent_id in self._live:
            return trace.set_span_in_context(self._live[span.parent_id])
        return super()._parent_context(span)

    def __call__(self, span):
        if isinstance(span.data, telemetry.AiStreamSpanData):
            span.set_as_current = True
        return super().__call__(span)


ai.experimental_telemetry.register(GatewayOtelAdapter(capture_content=True))

http_client = gateway_http_client(f"{os.environ['LITELLM_GATEWAY_URL']}/v1")
client = AsyncOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    http_client=http_client,
)
model = ai.Model(
    id=os.environ["LITELLM_MODEL"],
    provider=ai.get_provider("openai", client=client),
    protocol=OpenAIChatCompletionsProtocol(),
)


class research_agent(ai.Agent):  # noqa: N801 - the class name becomes gen_ai.agent.name
    pass


async def main() -> None:
    try:
        async with research_agent().run(model, [ai.user_message("What is an agent trace?")]) as stream:
            async for _ in stream:
                pass
        print(stream.output)
    finally:
        await http_client.aclose()
        trace.get_tracer_provider().force_flush()


asyncio.run(main())
