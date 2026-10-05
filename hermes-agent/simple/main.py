import os
from pathlib import Path

os.environ.setdefault("HERMES_HOME", str(Path(__file__).resolve().parents[1] / "home"))

from run_agent import AIAgent

agent = AIAgent(
    provider="litellm",
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    model=os.environ["LITELLM_MODEL"],
    enabled_toolsets=[],
    quiet_mode=True,
    skip_context_files=True,
    skip_memory=True,
)

print(agent.chat("What is an agent trace?"))
