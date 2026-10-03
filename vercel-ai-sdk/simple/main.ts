import { NodeSDK, tracing } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { OpenTelemetry } from "@ai-sdk/otel";
import { generateText, registerTelemetry } from "ai";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

const headers = { Authorization: `Bearer ${process.env.LITELLM_API_KEY}` };
const sdk = new NodeSDK({
  spanProcessors: [process.env.LITELLM_GATEWAY_URL, process.env.MOCK_LITELLM_GATEWAY_URL]
    .filter(Boolean)
    .map((url) => new tracing.BatchSpanProcessor(new OTLPTraceExporter({ url: `${url}/v1/traces`, headers }))),
});
sdk.start();
registerTelemetry(new OpenTelemetry());

const model = createOpenAICompatible({
  name: "litellm",
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
