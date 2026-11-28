"""Central configuration for Sim Malé."""

import sys
from pathlib import Path

# Windows consoles default to cp1252, which crashes on the bar chars / em dashes
# / Thaana we print. Force UTF-8 stdout so every entry point is safe.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# Load ANTHROPIC_API_KEY (and anything else) from a .env file if present.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is optional; env vars still work without it
    pass

# --- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

AGENTS_FILE = DATA_DIR / "agents.jsonl"          # the seeded synthetic population
RESULTS_DIR = DATA_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# --- Population ------------------------------------------------------------
POPULATION_SIZE = 10_000   # number of synthetic voters to generate
RANDOM_SEED = 42           # makes the generated population reproducible

# --- Models ----------------------------------------------------------------
# Two different paths, two different cost/quality trade-offs:
#
#   POLL_MODEL  — used when we fan out to thousands of agents at once (poll.py).
#                 This is where cost explodes, so the DEFAULT is Haiku 4.5.
#                 That is a deliberate COST decision you should review:
#                   - claude-haiku-4-5   cheapest, fastest, good enough for a vote + short reason
#                   - claude-sonnet-4-6  noticeably richer reasoning, ~5x the output cost
#                   - claude-opus-4-8    best reasoning, ~25x Haiku output cost — usually overkill at 10k scale
#
#   AGENT_MODEL — used for single-agent, interactive conversations (agent.py).
#                 Here you're paying for one call, so quality wins: Opus 4.8.
POLL_MODEL = "claude-haiku-4-5"
AGENT_MODEL = "claude-opus-4-8"

# Approx. blended USD price per 1M tokens, for the cost estimator in poll.py.
# (Batch API applies a further 50% discount on top of these.)
PRICING = {
    "claude-haiku-4-5":  {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8":   {"input": 5.00, "output": 25.00},
}

# --- Polling behaviour -----------------------------------------------------
# You rarely need to ask all 10k agents every time. Poll a representative
# sample and weight the results — far cheaper, and statistically fine.
DEFAULT_POLL_SAMPLE = 1_500   # set to POPULATION_SIZE to ask everyone
MAX_TOKENS_PER_VOTE = 400     # a vote + a one-paragraph reason fits easily
