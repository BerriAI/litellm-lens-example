import { NodeSDK, tracing } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { Mastra } from "@mastra/core";
import { Agent } from "@mastra/core/agent";
import { Observability } from "@mastra/observability";
import { OtelBridge } from "@mastra/otel-bridge";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { gatewayFetch } from "gateway-tracing";

const headers = { Authorization: `Bearer ${process.env.LITELLM_API_KEY}` };
const sdk = new NodeSDK({
  spanProcessors: [process.env.LITELLM_GATEWAY_URL, process.env.MOCK_LITELLM_GATEWAY_URL]
    .filter(Boolean)
    .map((url) => new tracing.BatchSpanProcessor(new OTLPTraceExporter({ url: `${url}/v1/traces`, headers }))),
});
sdk.start();

// Mastra's model router has no `fetch` option, so pass an AI SDK model that uses the gateway fetch.
const model = createOpenAICompatible({
  name: "litellm",
  fetch: gatewayFetch,
  baseURL: `${process.env.LITELLM_GATEWAY_URL}/v1`,
  apiKey: process.env.LITELLM_API_KEY,
})(process.env.LITELLM_MODEL!);

const researchAgent = new Agent({
  id: "research_agent",
  name: "research_agent",
  instructions: "Answer the question concisely.",
  model,
});

const mastra = new Mastra({
  agents: { researchAgent },
  observability: new Observability({
    configs: { default: { serviceName: "lens-mastra-simple", bridge: new OtelBridge() } },
  }),
});

try {
  const { text } = await mastra.getAgentById("research_agent").generate("What is an agent trace?");
  console.log(text);
} finally {
  await mastra.shutdown();
  await sdk.shutdown();
}
