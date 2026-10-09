# LiteLLM Lens examples

Runnable agent integrations that send traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens). Each integration’s README owns its setup instructions and is the source for its page in [the Lens documentation](https://docs.litellm.ai/docs/proxy/lens).

## Start without a gateway

Run [Lens with ClickHouse](https://github.com/BerriAI/lens/blob/main/deploy/lens/README.md), then follow [OpenAI Agents SDK](openai-agents/README.md) or [OpenTelemetry](opentelemetry/README.md) using the direct-provider environment template. Model calls use your provider credential; telemetry uses a separate Lens tracing key. The other framework examples retain their existing gateway model configuration

## Integrations

| Integration | Guide |
| --- | --- |
| DeepAgents | [Setup and examples](deepagents/README.md) |
| LangGraph | [Setup and examples](langgraph/README.md) |
| LangChain | [Setup and examples](langchain/README.md) |
| OpenAI Agents SDK | [Setup and examples](openai-agents/README.md) |
| Claude Agent SDK | [Setup and examples](claude-agent-sdk/README.md) |
| CrewAI | [Setup and examples](crewai/README.md) |
| Pydantic AI | [Setup and examples](pydantic-ai/README.md) |
| LlamaIndex | [Setup and examples](llamaindex/README.md) |
| Google ADK | [Setup and examples](google-adk/README.md) |
| Strands Agents | [Setup and examples](strands/README.md) |
| Vercel AI SDK (TypeScript) | [Setup and examples](vercel-ai-sdk-js/README.md) |
| Vercel AI SDK (Python) | [Setup and examples](vercel-ai-sdk-py/README.md) |
| Mastra | [Setup and examples](mastra/README.md) |
| Hermes Agent | [Setup and examples](hermes-agent/README.md) |
| OpenTelemetry | [Setup and examples](opentelemetry/README.md) |

## Coding agent sessions

[Claude Code](claude-code/README.md) and [Codex](codex/README.md) point to their maintained session-recording guides.

## Documentation publishing

[docs.json](docs.json) lists the published READMEs, their titles, descriptions, stable slugs, and sidebar categories. [DOCS.md](DOCS.md) describes the authoring format and the contract used by the [litellm-docs importer](https://github.com/BerriAI/litellm-docs/blob/main/scripts/sync-lens-docs.mjs).

## Shared tracing

The [shared gateway transport](shared/README.md) records request attempts and gateway call IDs for the examples that use it. The [local recorder](recorder/AGENTS.md) is an optional development tool for inspecting exported traces.
