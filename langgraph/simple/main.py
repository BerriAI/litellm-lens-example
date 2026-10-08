import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.auto_instrumentation import initialize
from opentelemetry.sdk.trace.export import BatchSpanProcessor

initialize()

headers = {"Authorization": f"Bearer {os.environ['LENS_TRACING_KEY']}"}
for url in filter(None, [os.environ["LENS_URL"], os.environ.get("MOCK_LITELLM_GATEWAY_URL")]):
    exporter = OTLPSpanExporter(f"{url}/v1/traces", headers=headers)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))

from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph

model = ChatOpenAI(
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    model=os.environ["LITELLM_MODEL"],
)

graph = StateGraph(MessagesState)
graph.add_node("call_model", lambda state: {"messages": [model.invoke(state["messages"])]})
graph.add_edge(START, "call_model")

agent = graph.compile(name="research_agent")
result = agent.invoke({"messages": [{"role": "user", "content": "What is an agent trace?"}]})
print(result["messages"][-1].content)
