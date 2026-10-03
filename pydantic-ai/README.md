# Pydantic AI

Send Pydantic AI traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single `research_agent` answers one question.
  ```sh
  uv run --env-file .env --package lens-pydantic-ai-simple simple/main.py
  ```
- `swarm`: `research_agent` delegates to `search_agent` and `writer_agent` through tools.
  ```sh
  uv run --env-file .env --package lens-pydantic-ai-swarm swarm/main.py
  ```
