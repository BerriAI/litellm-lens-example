# CrewAI

Send CrewAI traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env
```

- `simple`: a single-agent crew answering one question.
  ```sh
  uv run --env-file .env --package lens-crewai-simple simple/main.py
  ```
- `swarm`: a sequential crew where `research_agent` plans and briefs `search_agent` and `writer_agent`.
  ```sh
  uv run --env-file .env --package lens-crewai-swarm swarm/main.py
  ```
