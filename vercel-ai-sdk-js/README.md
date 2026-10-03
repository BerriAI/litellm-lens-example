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

Each provider request emits a `gateway.request` span and propagates its trace context to the gateway. Its `litellm.call_id` comes from the gateway response header, including streamed responses and retries

Run transport regressions with `npm test`. Validate real gateway streaming, retry and billed response loss with:

```sh
node --env-file=.env validate-attempts.ts streaming
node --env-file=.env validate-attempts.ts retry
node --env-file=.env validate-attempts.ts response-loss
```

The retry scenario replaces the first real billed response with a client-side HTTP 503. The response-loss scenario consumes the real billed response and fails the client stream. Neither scenario changes gateway or provider behavior
