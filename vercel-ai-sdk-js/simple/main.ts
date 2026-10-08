import { NodeSDK, tracing } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { OpenTelemetry } from "@ai-sdk/otel";
import { generateText, registerTelemetry } from "ai";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { gatewayFetch } from "gateway-tracing";

if (!process.env.LENS_URL || !process.env.LENS_TRACING_KEY) throw new Error("Set LENS_URL and LENS_TRACING_KEY from Lens tracing setup");

const headers = { Authorization: `Bearer ${process.env.LENS_TRACING_KEY}` };
// @ai-sdk/otel names agent spans `invoke_agent <model>`; use the agent name instead.
const nameAgentSpans: tracing.SpanProcessor = {
  onStart: (span) => {
    const agent = span.attributes["gen_ai.agent.name"];
    if (span.attributes["gen_ai.operation.name"] === "invoke_agent" && agent) span.updateName(`invoke_agent ${agent}`);
  },
  onEnd: () => {},
  forceFlush: async () => {},
  shutdown: async () => {},
};
const sdk = new NodeSDK({
  spanProcessors: [
    nameAgentSpans,
    ...[process.env.LENS_URL, process.env.MOCK_LITELLM_GATEWAY_URL]
      .filter(Boolean)
      .map((url) => new tracing.BatchSpanProcessor(new OTLPTraceExporter({ url: `${url}/v1/traces`, headers }))),
  ],
});
sdk.start();
registerTelemetry(new OpenTelemetry());

const model = createOpenAICompatible({
  name: "litellm",
  fetch: gatewayFetch,
  baseURL: `${process.env.LITELLM_GATEWAY_URL}/v1`,
  apiKey: process.env.LITELLM_API_KEY,
})(process.env.LITELLM_MODEL!);

try {
  const { text } = await generateText({
    model,
    prompt: "What is an agent trace?",
    telemetry: { isEnabled: true, functionId: "research_agent" },
  });
  console.log(text);
} finally {
  await sdk.shutdown();
}
