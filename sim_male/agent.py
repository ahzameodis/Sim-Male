"""
Single-agent interaction + a small multi-agent conversation framework (step 2).

- ask_agent()          : ask one resident one question (Opus, high quality).
- AgentConversation    : let several residents talk to each other in a round-robin,
                         each seeing what the others said — a focus group.

For polling thousands of agents at once, use poll.py (Batch API) instead — it is
far cheaper and faster than looping ask_agent() 10,000 times.
"""

from __future__ import annotations

import anthropic

from . import config
from .persona import build_system_blocks


def _client() -> anthropic.Anthropic:
    # Reads ANTHROPIC_API_KEY from the environment (.env is loaded in run_demo.py
    # / poll.py). Don't hard-code keys.
    return anthropic.Anthropic()


def ask_agent(agent: dict, question: str, *, model: str | None = None,
              client: anthropic.Anthropic | None = None) -> str:
    """Ask a single resident a free-form question and return their reply."""
    client = client or _client()
    resp = client.messages.create(
        model=model or config.AGENT_MODEL,
        max_tokens=600,
        system=build_system_blocks(agent),
        messages=[{"role": "user", "content": question}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


class AgentConversation:
    """
    A lightweight focus-group simulator: a handful of agents discuss a topic,
    taking turns, each able to react to what was said before them.

    Usage:
        convo = AgentConversation([a1, a2, a3])
        for turn in convo.run("Should the government build more flats in Hulhumalé?", rounds=2):
            print(turn["speaker"], ":", turn["text"])
    """

    def __init__(self, agents: list[dict], *, model: str | None = None):
        if not 2 <= len(agents) <= 8:
            raise ValueError("Use 2–8 agents for a readable focus group.")
        self.agents = agents
        self.model = model or config.AGENT_MODEL
        self.client = _client()
        self.transcript: list[dict] = []

    def _label(self, agent: dict) -> str:
        return f"{agent['district']} {agent['employment'].replace('_', ' ')} ({agent['party_lean']})"

    def run(self, topic: str, *, rounds: int = 1):
        """Yield each turn as {'speaker', 'agent_id', 'text'}."""
        for _ in range(rounds):
            for agent in self.agents:
                history = "\n".join(
                    f"- {t['speaker']}: {t['text']}" for t in self.transcript
                ) or "(You are the first to speak.)"
                prompt = (
                    f"You are in a community discussion with other Malé residents "
                    f"about this topic:\n\n  \"{topic}\"\n\n"
                    f"What has been said so far:\n{history}\n\n"
                    f"Give your own short take (2–4 sentences). React to others if "
                    f"you disagree, but speak as yourself."
                )
                resp = self.client.messages.create(
                    model=self.model,
                    max_tokens=400,
                    system=build_system_blocks(agent),
                    messages=[{"role": "user", "content": prompt}],
                )
                text = "".join(b.text for b in resp.content if b.type == "text").strip()
                turn = {"speaker": self._label(agent), "agent_id": agent["id"], "text": text}
                self.transcript.append(turn)
                yield turn
