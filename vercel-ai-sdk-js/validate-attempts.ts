import { NodeSDK, tracing } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { OpenTelemetry } from "@ai-sdk/otel";
import { generateText, registerTelemetry, streamText } from "ai";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { createGatewayFetch } from "gateway-tracing";

const scenario = process.argv[2];
if (!["streaming", "retry", "response-loss"].includes(scenario)) throw new Error("Expected streaming, retry or response-loss");
const sdk = new NodeSDK({
  spanProcessors: [process.env.LITELLM_GATEWAY_URL, process.env.MOCK_LITELLM_GATEWAY_URL]
    .filter(Boolean)
    .map((url) => new tracing.BatchSpanProcessor(new OTLPTraceExporter({
      url: `${url}/v1/traces`, headers: { Authorization: `Bearer ${process.env.LITELLM_API_KEY}` },
    }))),
});
sdk.start();
registerTelemetry(new OpenTelemetry());
let injected = false;
const transport: typeof fetch = async (input, init) => {
  const response = await fetch(input, init);
  if (scenario === "retry" && !injected && response.ok) {
    injected = true;
    await response.arrayBuffer();
    return new Response("Client validation injected response loss", { status: 503, headers: response.headers });
  }
  if (scenario === "response-loss" && response.ok) {
    await response.arrayBuffer();
    return new Response(new ReadableStream({ start(controller) { controller.error(new Error("Client lost billed response")); } }), {
      status: response.status, headers: response.headers,
    });
  }
  return response;
};
const model = createOpenAICompatible({
  name: "litellm", baseURL: `${process.env.LITELLM_GATEWAY_URL}/v1`, apiKey: process.env.LITELLM_API_KEY,
  fetch: createGatewayFetch({ transport }),
})(process.env.LITELLM_MODEL!);
try {
  const options = { model, prompt: "Reply with one short sentence about agent traces.", maxRetries: scenario === "retry" ? 1 : 0,
    telemetry: { isEnabled: true, functionId: `vercel_${scenario}` } };
  if (scenario === "response-loss" || scenario === "streaming") {
    const result = streamText(options);
    for await (const text of result.textStream) process.stdout.write(text);
    const finishReason = await result.finishReason;
    console.log(JSON.stringify({ scenario, finishReason }));
  } else {
    await generateText(options);
    console.log(JSON.stringify({ scenario, injected, result: "success" }));
  }
} catch (error) {
  console.log(JSON.stringify({ scenario, result: "expected client error", error: error instanceof Error ? error.message : String(error) }));
  if (scenario !== "response-loss") process.exitCode = 1;
} finally {
  await sdk.shutdown();
}
