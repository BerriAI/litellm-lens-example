# Claude Code

Send your personal Claude Code sessions to [LiteLLM Lens](https://docs.litellm.ai/docs/proxy/lens). This folder links to the maintained integration instructions.

## Prerequisites

You need Claude Code, [Lens installed alongside LiteLLM](https://docs.litellm.ai/docs/proxy/lens/deployment#configure-an-existing-proxy), and a dedicated Lens tracing key. Open **Lens > Traces > Set up tracing**, copy the full **Traces endpoint** under **Connection details**, and click **Generate tracing key**. Ask your administrator for these if you cannot create a tracing key.

## Setup

Follow the [Lens coding agent setup guide](https://docs.litellm.ai/docs/proxy/lens/coding_agents) for gateway-specific instructions. See the [Claude Code monitoring guide](https://code.claude.com/docs/en/monitoring-usage) for the integration’s configuration and supported telemetry.

## Verify the trace

Complete a new session turn, then open **Lens > Traces** on your gateway. Find the session using the agent name configured by the integration and inspect its recorded activity.

## Troubleshooting

If the session is missing, check the setup guide’s recording and export instructions, the gateway URL, and the key. Check the maintained integration documentation for supported activity and platform requirements.
