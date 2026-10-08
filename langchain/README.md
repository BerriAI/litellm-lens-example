# LangChain

Send LangChain traces to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens) using the runnable examples in this repository.

## Prerequisites

You need a LiteLLM gateway with [tracing enabled](https://docs.litellm.ai/docs/proxy/lens#configure-an-existing-proxy), a LiteLLM key, and a configured model alias. The swarm example needs a model that supports tool calls. The Lens service receives and stores traces separately from the gateway and runs investigations. Generate a dedicated tracing key in **Lens > Traces > Set up tracing**.

Install uv. It uses the checked-in Python version and resolves each example’s dependencies from its uv workspace.

## Configuration

For a fresh checkout:

```bash
git clone https://github.com/BerriAI/litellm-lens-example.git
cd litellm-lens-example/langchain
cp .env.example .env
```

If you already cloned the repository, run the remaining commands from `langchain/`. Copy [.env.example](.env.example) to `.env` if it does not exist, then set:

| Variable | Value |
| --- | --- |
| `LITELLM_GATEWAY_URL` | Your gateway’s base URL without a trailing slash or `/v1`, for example `http://localhost:4002` |
| `LITELLM_API_KEY` | Your LiteLLM model key |
| `LENS_URL` | The ingestion URL from Lens tracing setup, for example `http://localhost:4318` or `https://gateway.example/lens-ingest` |
| `LENS_TRACING_KEY` | The dedicated tracing key from Lens tracing setup |
| `LITELLM_MODEL` | A model alias configured on your gateway |

The checked-in values target a local development gateway. Replace them for your deployment. Keep the exporter settings from `.env.example`; the examples configure their trace exporters in code. They send traces to `LENS_URL/v1/traces` with the tracing key as a bearer token.

Leave `MOCK_LITELLM_GATEWAY_URL` unset unless you intend to send an additional trace copy to the local [recorder](../recorder/AGENTS.md).

## Run an example

### Simple agent

A `research_agent` built with `create_agent` answers one question.

```bash
uv run --env-file .env --package lens-langchain-simple simple/main.py
```

See [simple/main.py](simple/main.py) for the implementation.

### Agent swarm

A coordinator invokes `search_agent` and `writer_agent` through search and write tools.

```bash
uv run --env-file .env --package lens-langchain-swarm swarm/main.py
```

See [swarm/main.py](swarm/main.py) for the implementation.

## Verify the trace

After the example prints its answer, open **Lens > Traces** on your gateway and select the new run. Look for the run associated with `research_agent`. Inspect the input, output, and model spans. For the swarm, inspect the specialist activity described above; its exact span layout depends on the framework.

## How tracing works

OpenInference instruments LangChain runs. Each create_agent graph has an explicit name, and delegated runs inherit the coordinator’s trace context.

## Troubleshooting

If model calls fail, check the gateway URL, key, and model alias. If an answer appears but the trace is missing, check the terminal for exporter errors and confirm the Lens ingestion service is reachable with your tracing key. A model call succeeding does not confirm that its trace export succeeded.
