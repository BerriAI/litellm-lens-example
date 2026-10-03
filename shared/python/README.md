Python half of the shared gateway tracing contract described in `../README.md`

`gateway_http_client(base_url)` returns an async client and `gateway_sync_http_client(base_url)` a sync one. Import them from `gateway_tracing.httpx2` (SDKs on `openai>=3`) or `gateway_tracing.httpx` (SDKs on `openai<3`), matching the HTTP library the SDK's OpenAI client expects, and pass the client as the SDK's `http_client`. Both modules are built from one implementation in `_transport.py`; `_attempt.py` owns the span and `contract.py` the names LiteLLM matches on

Each POST under `base_url` becomes a child `gateway.request` span. Other requests pass through untouched. Pass `transport=` to wrap a custom or mock transport

Install with the HTTP library extra: `gateway-tracing[httpx]` or `gateway-tracing[httpx2]`, as an editable path source so SDK environments follow this folder. Run the regressions from an SDK environment with `python -m unittest discover -s ../shared/python/tests -v`. Set `GATEWAY_HTTP_MODULE=httpx` to test the HTTPX adapter. The default tests HTTPX2
