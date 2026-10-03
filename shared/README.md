# Shared gateway tracing

`shared/js` (`gateway-tracing` npm workspace) and `shared/python` (`gateway-tracing` uv package) wrap an SDK's HTTP client so every physical request to the LiteLLM gateway becomes a span that LiteLLM can join to its spend log row. Both implement the same contract; `shared/js/contract.ts` and `shared/python/gateway_tracing/contract.py` hold its names and the tests on each side assert them

## Contract

LiteLLM reads these from the span (`litellm-rust/crates/traces/src/normalize/instrumentation/http_client.rs` and `resolve/spend.rs`, [BerriAI/litellm#44421](https://github.com/BerriAI/litellm/pull/44421)):

| Side | Value | Purpose |
| --- | --- | --- |
| Tracer scope | `litellm.gateway.client` | Together with the next three, marks the span as a gateway attempt |
| Span name | `gateway.request` | |
| Attribute | `litellm.gateway.attempt = true` | |
| Attribute | `http.request.method = POST` | Only POSTs are model calls; other requests pass through untraced |
| Request header | `traceparent` carrying the attempt span's own IDs | LiteLLM logs them as the spend row's `trace_id` and `span_id` |
| Response header | `x-litellm-call-id` → attribute `litellm.call_id` | Matches the spend row's `litellm_call_id`, with a fallback to `request_id` on older rows |

An attempt resolves to spend only when both keys agree on one row owned by the same team and key. Each SDK retry is its own attempt with its own IDs, so a billed failure and its successful retry stay distinct rows. The span ends when the response body finishes, errors or is closed, so a streamed response keeps one span for its whole life, and the adapter never changes the current span, so later SDK spans keep their parent

Only the URL's scheme, host, port and path are recorded (`url.full`, `server.address`). Authentication headers, query strings, bodies and exception messages are excluded; failures record `error.type` and an error status

## Usage

- TypeScript: `import { gatewayFetch, createGatewayFetch } from "gateway-tracing"` and pass it as the provider's `fetch`. `createGatewayFetch({ baseUrl, transport })` limits tracing to requests under `baseUrl` and wraps a custom transport. Test with `npm test -w gateway-tracing` from the repo root
- Python: `from gateway_tracing.httpx2 import gateway_http_client, gateway_sync_http_client` (or `.httpx` for SDKs on `openai<3`), and pass the client as the SDK's `http_client`. See `shared/python/README.md`

## Where it is used

| Example | Adapter | Why |
| --- | --- | --- |
| `vercel-ai-sdk-js`, `mastra` | `gatewayFetch` | Provider `fetch` option |
| `pydantic-ai`, `vercel-ai-sdk-py`, `openai-agents` | `httpx2` async | `AsyncOpenAI(http_client=...)`; the instrumentor keeps the model span current during the request |
| `opentelemetry` | `httpx2` sync | `OpenAI(http_client=...)`; `openinference-instrumentation-openai` keeps `ChatCompletion` current |
| `strands`, `google-adk` | `httpx` async | SDKs still on `openai<3` |

Not wired, and why:

- `langchain`, `langgraph`, `deepagents`, `llamaindex`: their OpenInference instrumentors are callback based and deliberately never attach the LLM span to the current context, so an attempt span would land in a separate trace. They join spend through the provider response id in the LLM span instead
- `crewai`: `LLM(client_params=...)` is applied to both the sync and async OpenAI clients, and the async client rejects an `httpx.Client`
- `claude-agent-sdk`: model calls happen inside the bundled CLI, which owns its HTTP client. Its local adapter in `claude-agent-sdk/gateway.py` surfaces the provider message id instead
