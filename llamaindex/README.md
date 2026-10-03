# LlamaIndex

Send LlamaIndex traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single `FunctionAgent` answers one prompt.
  ```sh
  uv run --env-file .env --package lens-llamaindex-simple simple/main.py
  ```
- `swarm`: an `AgentWorkflow` where `research_agent` hands off to `search_agent`, which hands off to `writer_agent`.
  ```sh
  uv run --env-file .env --package lens-llamaindex-swarm swarm/main.py
  ```
