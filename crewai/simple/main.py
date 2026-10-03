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

from crewai import LLM, Agent, Crew, Task

model = LLM(
    model=f"openai/{os.environ['LITELLM_MODEL']}",
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
)

agent = Agent(
    role="research_agent",
    goal="Answer questions clearly",
    backstory="You explain technical concepts.",
    llm=model,
)
task = Task(description="{question}", expected_output="A short answer", agent=agent)
crew = Crew(name="research_crew", agents=[agent], tasks=[task])
print(crew.kickoff(inputs={"question": "What is an agent trace?"}))
