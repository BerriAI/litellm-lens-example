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
