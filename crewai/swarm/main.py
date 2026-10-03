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

research_agent = Agent(
    role="research_agent",
    goal="Plan how to answer questions and brief your team",
    backstory="You coordinate a search specialist and a writer.",
    llm=model,
)
search_agent = Agent(
    role="search_agent",
    goal="Gather key facts for the research plan",
    backstory="You find relevant technical facts.",
    llm=model,
)
writer_agent = Agent(
    role="writer_agent",
    goal="Answer questions clearly from the gathered facts",
    backstory="You explain technical concepts.",
    llm=model,
)
question = "What is an agent trace?"
tasks = [
    Task(description=f"Plan how to answer: {question}", expected_output="A short research plan", agent=research_agent),
    Task(description=f"Gather facts for: {question}", expected_output="A few key facts", agent=search_agent),
    Task(description=question, expected_output="A short answer", agent=writer_agent),
]
print(Crew(agents=[research_agent, search_agent, writer_agent], tasks=tasks).kickoff())
