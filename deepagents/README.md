# DeepAgents

Send DeepAgents traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single deep agent answers a question.
  ```sh
  uv run --env-file .env --package lens-deepagents-simple simple/main.py
  ```
- `swarm`: a deep agent delegates to `search_agent` and `writer_agent` subagents via the `task` tool.
  ```sh
  uv run --env-file .env --package lens-deepagents-swarm swarm/main.py
  ```
