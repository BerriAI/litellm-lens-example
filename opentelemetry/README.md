# OpenTelemetry

Send OpenTelemetry traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single manual `research_agent` span wrapping one OpenAI call.
  ```sh
  uv run --env-file .env --package lens-opentelemetry-simple simple/main.py
  ```
- `swarm`: a `research_agent` span delegating to `search_agent` and `writer_agent` child spans, each making its own OpenAI call.
  ```sh
  uv run --env-file .env --package lens-opentelemetry-swarm swarm/main.py
  ```
