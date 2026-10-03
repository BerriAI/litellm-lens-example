import assert from "node:assert/strict";
import { test } from "node:test";
import { NodeSDK, tracing } from "@opentelemetry/sdk-node";
import { diag, DiagLogLevel, SpanStatusCode, trace } from "@opentelemetry/api";
import { createGatewayFetch } from "./gateway-fetch.ts";

const warnings: unknown[][] = [];
diag.setLogger({ warn: (...args) => warnings.push(args), error: () => {}, info: () => {}, debug: () => {}, verbose: () => {} }, DiagLogLevel.WARN);

const exporter = new tracing.InMemorySpanExporter();
const processor = new tracing.SimpleSpanProcessor(exporter);
const sdk = new NodeSDK({ spanProcessors: [processor] });
sdk.start();

await test("request attempts retain ownership and IDs through body errors and cancellation", async () => {
  const tracer = trace.getTracer("test.sdk");
  await tracer.startActiveSpan("sdk.call", async (parent) => {
    const cases = ["success", "error", "cancel"] as const;
    for (const scenario of cases) {
      const transport: typeof fetch = async (input) => {
        const request = input as Request;
        const active = trace.getActiveSpan()!.spanContext();
        assert.equal(request.headers.get("traceparent"), `00-${active.traceId}-${active.spanId}-01`);
        const body = new ReadableStream<Uint8Array>({
          pull(controller) {
            if (scenario === "error") controller.error(new Error("lost response"));
            else { controller.enqueue(new TextEncoder().encode("ok")); controller.close(); }
          },
        });
        return new Response(body, { headers: { "x-litellm-call-id": scenario } });
      };
      const response = await createGatewayFetch(transport)("http://localhost/v1/chat/completions?secret=hidden", { method: "POST" });
      if (scenario === "error") await assert.rejects(response.text(), /lost response/);
      else if (scenario === "cancel") await response.body!.cancel();
      else assert.equal(await response.text(), "ok");
    }
    parent.end();
  });
  await processor.forceFlush();
  const spans = exporter.getFinishedSpans();
  const parent = spans.find((span) => span.name === "sdk.call")!;
  const attempts = spans.filter((span) => span.name === "gateway.request");
  assert.equal(attempts.length, 3);
  for (const span of attempts) {
    assert.equal(span.spanContext().traceId, parent.spanContext().traceId);
    assert.equal(span.parentSpanContext?.spanId, parent.spanContext().spanId);
    assert.equal(span.attributes["url.full"], "http://localhost/v1/chat/completions");
    assert.equal(span.attributes["http.request.method"], "POST");
    assert.equal(span.attributes["litellm.gateway.attempt"], true);
  }
  assert.deepEqual(attempts.map((span) => span.attributes["litellm.call_id"]).sort(), ["cancel", "error", "success"]);
  assert.equal(new Set(attempts.map((span) => span.spanContext().spanId)).size, attempts.length);
  const beforeFailures = spans.length;
  await assert.rejects(createGatewayFetch()("invalid URL"), TypeError);
  const failedTransport: typeof fetch = async () => { throw new Error("Connection lost"); };
  await assert.rejects(createGatewayFetch(failedTransport)("http://localhost/v1/chat/completions", { method: "POST" }), /Connection lost/);
  const pendingTransport: typeof fetch = async () => new Response(new ReadableStream({ pull: () => new Promise(() => {}) }), {
    headers: { "x-litellm-call-id": "pending-cancel" },
  });
  const pendingResponse = await createGatewayFetch(pendingTransport)("http://localhost/v1/chat/completions", { method: "POST" });
  const pendingReader = pendingResponse.body!.getReader();
  const pendingRead = pendingReader.read();
  await pendingReader.cancel();
  await pendingRead;
  await processor.forceFlush();
  const failures = exporter.getFinishedSpans().slice(beforeFailures);
  assert.equal(failures.length, 3);
  assert.equal(failures[0].status.code, SpanStatusCode.ERROR);
  assert.equal(failures[1].status.code, SpanStatusCode.ERROR);
  assert.equal(failures[2].attributes["litellm.call_id"], "pending-cancel");
  assert.deepEqual(warnings, []);
  await sdk.shutdown();
});
