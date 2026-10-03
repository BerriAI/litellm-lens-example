# Claude Agent SDK

Send Claude Agent SDK traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: one `research_agent` answering a question.
  ```sh
  uv run --env-file .env --package lens-claude-agent-sdk-simple simple/main.py
  ```
- `swarm`: `research_agent` delegating to `search_agent` and `writer_agent` subagents.
  ```sh
  uv run --env-file .env --package lens-claude-agent-sdk-swarm swarm/main.py
  ```

To link model spans to spend logs, start the local adapter in a separate terminal. It adds the actual Anthropic message ID as the `request-id` response header, which the CLI records on its model spans. Streaming response bytes pass through unchanged

```sh
LITELLM_GATEWAY_URL=http://localhost:4002 \
MOCK_LITELLM_GATEWAY_URL=http://localhost:4318 \
uv run --package lens-claude-agent-sdk-simple gateway.py
```

Run the examples against the adapter. Keep `MOCK_LITELLM_GATEWAY_URL` empty here because the adapter already copies SDK and CLI trace exports to the recorder and forwards them to port 4002

```sh
LITELLM_GATEWAY_URL=http://localhost:4319 \
LITELLM_MODEL=openai/gpt-6-luna \
MOCK_LITELLM_GATEWAY_URL= \
uv run --env-file .env --package lens-claude-agent-sdk-simple simple/main.py

LITELLM_GATEWAY_URL=http://localhost:4319 \
LITELLM_MODEL=openai/gpt-6-luna \
MOCK_LITELLM_GATEWAY_URL= \
uv run --env-file .env --package lens-claude-agent-sdk-swarm swarm/main.py
```

The recorder is optional. Omit its environment variable when only sending to LiteLLM. The adapter binds to localhost, and `CLAUDE_GATEWAY_PORT` changes its default port 4319

```sh
uv run --package lens-claude-agent-sdk-simple python -m unittest discover -s . -p test_gateway.py
```
