import { SpanKind, SpanStatusCode, trace } from "@opentelemetry/api";
import { ATTEMPT_ATTRIBUTE, CALL_ID_ATTRIBUTE, CALL_ID_HEADER, METHOD, SCOPE, SPAN_NAME } from "./contract.ts";

export * as contract from "./contract.ts";

export interface GatewayFetchOptions {
  /** Only requests under this URL are traced. Without it, every POST through the fetch is treated as a gateway request. */
  baseUrl?: string;
  transport?: typeof fetch;
}

const tracer = trace.getTracer(SCOPE);

const underBase = (url: URL, base: URL | undefined): boolean =>
  base === undefined || (url.origin === base.origin && url.pathname.startsWith(`${base.pathname.replace(/\/$/, "")}/`));

export const createGatewayFetch = ({ baseUrl, transport = fetch }: GatewayFetchOptions = {}): typeof fetch => {
  const base = baseUrl === undefined ? undefined : new URL(baseUrl);
  return async (input, init) => {
    const request = new Request(input, init);
    const url = new URL(request.url);
    if (request.method !== METHOD || !underBase(url, base)) return transport(request);
    return tracer.startActiveSpan(SPAN_NAME, { kind: SpanKind.CLIENT }, async (span) => {
      let finished = false;
      const finish = (error?: unknown) => {
        if (finished) return;
        finished = true;
        if (error !== undefined) {
          span.setAttribute("error.type", error instanceof Error ? error.name : typeof error);
          span.setStatus({ code: SpanStatusCode.ERROR });
        }
        span.end();
      };
      try {
        span.setAttributes({
          [ATTEMPT_ATTRIBUTE]: true,
          "http.request.method": request.method,
          "url.full": `${url.origin}${url.pathname}`,
          "server.address": url.hostname,
        });
        const spanContext = span.spanContext();
        request.headers.set(
          "traceparent",
          `00-${spanContext.traceId}-${spanContext.spanId}-${spanContext.traceFlags.toString(16).padStart(2, "0")}`,
        );
        const response = await transport(request);
        span.setAttribute("http.response.status_code", response.status);
        const callId = response.headers.get(CALL_ID_HEADER);
        if (callId) span.setAttribute(CALL_ID_ATTRIBUTE, callId);
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
              finish(error);
              controller.error(error);
            }
          },
          async cancel(reason) {
            finish();
            await reader.cancel(reason);
          },
        });
        return new Response(body, { status: response.status, statusText: response.statusText, headers: response.headers });
      } catch (error) {
        finish(error);
        throw error;
      }
    });
  };
};

export const gatewayFetch = createGatewayFetch();
