# LangChain

Send LangChain traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single `research_agent` built with `create_agent`.
  ```sh
  uv run --env-file .env --package lens-langchain-simple simple/main.py
  ```
- `swarm`: `research_agent` delegates to `search_agent` and `writer_agent`, each wrapped as a tool.
  ```sh
  uv run --env-file .env --package lens-langchain-swarm swarm/main.py
  ```
