# LangGraph

Send LangGraph traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single-node graph agent.
  ```sh
  uv run --env-file .env --package lens-langgraph-simple simple/main.py
  ```
- `swarm`: a `research_agent` graph that delegates to `search_agent` and `writer_agent` subgraphs.
  ```sh
  uv run --env-file .env --package lens-langgraph-swarm swarm/main.py
  ```
