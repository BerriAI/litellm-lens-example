import { SpanKind, SpanStatusCode, trace } from "@opentelemetry/api";

const tracer = trace.getTracer("litellm.gateway.client");

export const createGatewayFetch = (transport: typeof fetch = fetch): typeof fetch => async (input, init) =>
  tracer.startActiveSpan("gateway.request", { kind: SpanKind.CLIENT }, async (span) => {
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      span.end();
    };
    try {
      const request = new Request(input, init);
      const url = new URL(request.url);
      span.setAttributes({
        "http.request.method": request.method,
        "url.full": `${url.origin}${url.pathname}`,
        "litellm.gateway.attempt": true,
      });
      const spanContext = span.spanContext();
      request.headers.set(
        "traceparent",
        `00-${spanContext.traceId}-${spanContext.spanId}-${spanContext.traceFlags.toString(16).padStart(2, "0")}`,
      );
      const response = await transport(request);
      span.setAttribute("http.response.status_code", response.status);
      const callId = response.headers.get("x-litellm-call-id");
      if (callId) span.setAttribute("litellm.call_id", callId);
      if (!response.ok) span.setStatus({ code: SpanStatusCode.ERROR });
      if (!response.body) {
        finish();
        return response;
      }
      const reader = response.body.getReader();
      const body = new ReadableStream<Uint8Array>({
        async pull(controller) {
          try {
            const result = await reader.read();
            if (finished) return;
            if (result.done) {
              controller.close();
              finish();
            } else {
              controller.enqueue(result.value);
            }
          } catch (error) {
            span.setStatus({ code: SpanStatusCode.ERROR });
            finish();
            controller.error(error);
          }
        },
        async cancel(reason) {
          finish();
          await reader.cancel(reason);
        },
      });
      return new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR });
      finish();
      throw error;
    }
  });

export const gatewayFetch = createGatewayFetch();
