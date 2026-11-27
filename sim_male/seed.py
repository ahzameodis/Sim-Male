"""
Seed the simulation: generate the synthetic Malé electorate and save it.

Run:
    python -m sim_male.seed
    python -m sim_male.seed --n 10000 --seed 42

Output: data/agents.jsonl  (one JSON agent per line) + a printed summary so you
can eyeball whether the marginals look like real Malé before spending on polls.
"""

import argparse
import json
import random
from collections import Counter

from . import config
from .demographics import sample_persona
from .map_data import assign_coordinates


def generate(n: int, seed: int, out_path) -> list[dict]:
    rng = random.Random(seed)
    agents = []
    for i in range(n):
        persona = sample_persona(rng, i)
        lat, lon = assign_coordinates(rng, persona["district"])
        persona["lat"] = lat
        persona["lon"] = lon
        agents.append(persona)

    with open(out_path, "w", encoding="utf-8") as f:
        for a in agents:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return agents


def load_agents(path=config.AGENTS_FILE) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _summary(agents: list[dict]) -> None:
    n = len(agents)
    print(f"\nGenerated {n:,} synthetic Malé voters -> {config.AGENTS_FILE}\n")
    for field in ("district", "age_band", "housing", "party_lean",
                  "foreign_policy_lean", "origin"):
        print(f"  {field}:")
        counts = Counter(a[field] for a in agents)
        for value, c in counts.most_common():
            print(f"    {value:<18} {c/n:6.1%}  ({c:,})")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed the Sim Malé population.")
    ap.add_argument("--n", type=int, default=config.POPULATION_SIZE)
    ap.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    args = ap.parse_args()

    agents = generate(args.n, args.seed, config.AGENTS_FILE)
    _summary(agents)


if __name__ == "__main__":
    main()
