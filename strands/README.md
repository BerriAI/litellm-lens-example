# Strands Agents

Send Strands Agents traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

The examples use the shared gateway HTTP client to record each request attempt under its Strands chat span. Gateway call IDs come from response headers, so streaming and retries can be correlated with spend

```sh
cp .env.example .env
```

- `simple`: a single `research_agent` answers one question.
  ```sh
  uv run --env-file .env --package lens-strands-simple simple/main.py
  ```
- `swarm`: `research_agent` calls `search_agent` and `writer_agent` as tools.
  ```sh
  uv run --env-file .env --package lens-strands-swarm swarm/main.py
  ```
