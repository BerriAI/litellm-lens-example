# Claude Code

Send your personal Claude Code sessions to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens). This folder links to the maintained integration instructions.

## Prerequisites

You need Claude Code, a running [Lens installation](https://github.com/BerriAI/lens/blob/main/deploy/lens/README.md), and a dedicated Lens tracing key. Lens can run with ClickHouse alone; keep your coding agent's existing model login and provider

## Setup

Follow the [Lens coding agent setup guide](https://docs.litellm.ai/docs/proxy/lens/coding_agents) for the tracing endpoint and key instructions. See the [Claude Code monitoring guide](https://code.claude.com/docs/en/monitoring-usage) for the integration’s configuration and supported telemetry.

## Verify the trace

Complete a new session turn, then open **Lens > Traces** in your standalone or embedded Lens UI. Find the session using the agent name configured by the integration and inspect its recorded activity.

## Troubleshooting

If the session is missing, check the setup guide’s recording and export instructions, the Lens ingestion URL, and the key. Check the maintained integration documentation for supported activity and platform requirements.
