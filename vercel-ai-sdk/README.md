# Vercel AI SDK

Send Vercel AI SDK traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens).

```sh
cp .env.example .env && npm install
```

- `simple`: a single `generateText` call traced as `research_agent`.
  ```sh
  node --env-file=.env simple/main.ts
  ```
- `swarm`: `research_agent` delegates to `search_agent` and `writer_agent`, tools that each run their own `generateText`.
  ```sh
  node --env-file=.env swarm/main.ts
  ```
