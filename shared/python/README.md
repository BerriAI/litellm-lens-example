`gateway_http_client(base_url)` creates an async HTTP client for a LiteLLM gateway. Import it from `gateway_tracing.httpx` or `gateway_tracing.httpx2`, matching the client's HTTP library

Pass the client into the SDK's supported HTTP client parameter. Each outgoing POST to the configured gateway gets a child `gateway.request` span in the `litellm.gateway.client` scope. Its trace context is injected into the request, and the gateway's `x-litellm-call-id` response header is recorded on that span

The span stays open until the response body finishes or closes. Retries produce separate spans. Transport failures and cancellation end the span and preserve the original exception. The adapter never changes the current span while a stream yields data, so later SDK spans keep their correct parent

Only the URL's scheme, host, port, and path are recorded. Authentication headers, query strings, request bodies, response bodies, and exception messages are excluded

Install with the HTTP library extra: `gateway-tracing[httpx]` or `gateway-tracing[httpx2]`. Run the regressions from an SDK environment with `python -m unittest discover -s ../gateway-tracing/tests -v`. Set `GATEWAY_HTTP_MODULE=httpx` to test the HTTPX adapter. The default tests HTTPX2
