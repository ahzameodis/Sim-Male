"""
A cheap end-to-end smoke test of Sim Malé — no Batch API, just a few live calls.

It will:
  1. Seed a small population if data/agents.jsonl doesn't exist.
  2. Ask 3 individual residents the same question (Opus).
  3. Run a short 3-person focus group on a local topic.

This costs a few cents. The full 10k poll lives in `python -m sim_male.poll`.

    python run_demo.py
"""

import os
import random

from sim_male import config
from sim_male.seed import generate, load_agents
from sim_male.agent import ask_agent, AgentConversation


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key."
        )

    if not config.AGENTS_FILE.exists():
        print("No population found — seeding 500 agents for the demo...")
        generate(500, config.RANDOM_SEED, config.AGENTS_FILE)

    agents = load_agents()
    rng = random.Random(1)
    sample = rng.sample(agents, 3)

    question = "How worried are you about the cost of housing in Malé, and why?"
    print("\n--- THREE INDIVIDUAL RESIDENTS ---\n")
    for a in sample:
        who = f"{a['district']} · {a['employment'].replace('_',' ')} · {a['housing']} · {a['party_lean']}"
        print(f"[{who}]")
        print(ask_agent(a, question), "\n")

    print("\n--- FOCUS GROUP ---\n")
    topic = "Should the government prioritise building affordable flats over new roads and bridges?"
    convo = AgentConversation(sample)
    for turn in convo.run(topic, rounds=1):
        print(f"{turn['speaker']}:\n  {turn['text']}\n")


if __name__ == "__main__":
    main()
