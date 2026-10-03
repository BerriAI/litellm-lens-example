"""The span contract LiteLLM uses to join a gateway request to its spend log row.

LiteLLM classifies a span as a gateway attempt when its scope is SCOPE, its name is SPAN_NAME, ATTEMPT_ATTRIBUTE is
true and the request method is METHOD. The attempt span's own trace and span IDs travel to the gateway in
`traceparent`, and the gateway's CALL_ID_HEADER response header is recorded as CALL_ID_ATTRIBUTE. Both must agree
with the spend row: see `litellm-rust/crates/traces/src/normalize/instrumentation/http_client.rs` and
`resolve/spend.rs` in https://github.com/BerriAI/litellm/pull/44421.
"""

from typing import Final

SCOPE: Final = "litellm.gateway.client"
SPAN_NAME: Final = "gateway.request"
METHOD: Final = "POST"
ATTEMPT_ATTRIBUTE: Final = "litellm.gateway.attempt"
CALL_ID_ATTRIBUTE: Final = "litellm.call_id"
CALL_ID_HEADER: Final = "x-litellm-call-id"
