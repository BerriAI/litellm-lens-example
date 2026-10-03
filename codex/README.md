# Codex

Send your personal Codex sessions to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens). This folder links to the maintained integration instructions.

## Prerequisites

You need Codex, a LiteLLM gateway with [tracing enabled](https://docs.litellm.ai/docs/proxy/lens#configure-an-existing-proxy), and a LiteLLM key.

## Setup

Follow the [Lens coding agent setup guide](https://docs.litellm.ai/docs/proxy/lens/coding_agents) for gateway-specific instructions. See the [LiteLLM Lens Codex integration](https://github.com/BerriAI/litellm-lens-codex-integration) for the integration’s configuration and supported telemetry.

## Verify the trace

Complete a new session turn, then open **Lens > Traces** on your gateway. Find the session using the agent name configured by the integration and inspect its recorded activity.

## Troubleshooting

If the session is missing, check the setup guide’s recording and export instructions, the gateway URL, and the key. Check the maintained integration documentation for supported activity and platform requirements.
