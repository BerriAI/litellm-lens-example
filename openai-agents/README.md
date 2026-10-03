# OpenAI Agents SDK

Send OpenAI Agents SDK traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single `research_agent` answering one question.
  ```sh
  uv run --env-file .env --package lens-openai-agents-simple simple/main.py
  ```
- `swarm`: `research_agent` delegates to `search_agent` and `writer_agent` exposed as tools.
  ```sh
  uv run --env-file .env --package lens-openai-agents-swarm swarm/main.py
  ```
