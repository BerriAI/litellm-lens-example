import os
import time
from pathlib import Path

os.environ.setdefault("HERMES_HOME", str(Path(__file__).resolve().parents[1] / "home"))

from hermes_cli.quiet_single_query import continue_quiet_notify_completions
from run_agent import AIAgent
from tools import async_delegation

agent = AIAgent(
    provider="litellm",
    base_url=f"{os.environ['LITELLM_GATEWAY_URL']}/v1",
    api_key=os.environ["LITELLM_API_KEY"],
    model=os.environ["LITELLM_MODEL"],
    enabled_toolsets=["delegation"],
    ephemeral_system_prompt=(
        "You coordinate specialists. In one delegate_task call, give one subagent fact gathering and another "
        "drafting. Answer from their results, without tools of your own."
    ),
    quiet_mode=True,
    skip_context_files=True,
    skip_memory=True,
)

turns = [agent.run_conversation("What is an agent trace?")]
while async_delegation.active_count():
    time.sleep(0.2)
continue_quiet_notify_completions(
    agent.session_id,
    lambda results: turns.append(agent.run_conversation(results, conversation_history=turns[-1]["messages"])),
)
print(turns[-1]["final_response"])
