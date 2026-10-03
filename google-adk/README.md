# Google ADK

Send Google ADK traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single `research_agent` answers one question.
  ```sh
  uv run --env-file .env --package lens-google-adk-simple simple/main.py
  ```
- `swarm`: `research_agent` calls `search_agent` and `writer_agent` as tools.
  ```sh
  uv run --env-file .env --package lens-google-adk-swarm swarm/main.py
  ```
