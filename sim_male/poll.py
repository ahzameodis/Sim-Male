"""
Poll the synthetic electorate (the heart of Sim Malé).

Asks a representative SAMPLE of agents a question with fixed options, using the
Message Batches API (async, 50% cheaper than one-by-one calls). Each agent
returns a structured vote so results parse cleanly. Then we weight and tally.

Run:
    python -m sim_male.poll "Who will you vote for?" "MDP" "PPM/PNC" "Undecided"
    python -m sim_male.poll --sample 2000 --model claude-sonnet-4-6 "..." "Yes" "No"

⚠️  Read the accuracy note in the README. Treat the percentages as DIRECTIONAL
    hypotheses, not predictions, until you have calibrated against a real poll.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from datetime import datetime

import anthropic

from . import config
from .persona import build_system_blocks
from .seed import load_agents


# --- vote schema -----------------------------------------------------------
def _vote_schema(options: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "choice": {"type": "string", "enum": options,
                       "description": "Exactly one option."},
            "confidence": {"type": "integer", "enum": [1, 2, 3, 4, 5],
                           "description": "1 = very unsure, 5 = certain."},
            "reason": {"type": "string",
                       "description": "One sentence, in character, why."},
        },
        "required": ["choice", "confidence", "reason"],
        "additionalProperties": False,
    }


def _question_prompt(question: str, options: list[str]) -> str:
    opts = "\n".join(f"  - {o}" for o in options)
    return (
        f"{question}\n\nChoose exactly one of these options:\n{opts}\n\n"
        f"Answer as yourself, the Malé resident described above. Pick the option "
        f"that best fits how you actually feel — even if reluctantly."
    )


# --- cost estimate ---------------------------------------------------------
def estimate_cost(n: int, model: str) -> float:
    """Very rough USD estimate for a batch poll (batch = 50% off)."""
    price = config.PRICING.get(model, config.PRICING["claude-haiku-4-5"])
    # ~1300 tokens city context (cached after first), ~250 persona+question, ~120 out.
    in_tokens = 1550
    out_tokens = 120
    cost = n * (in_tokens * price["input"] + out_tokens * price["output"]) / 1_000_000
    return cost * 0.5  # batch discount


# --- run a poll ------------------------------------------------------------
def run_poll(question: str, options: list[str], *, sample: int | None = None,
             model: str | None = None, poll_all: bool = False,
             seed: int = 0) -> dict:
    import random

    model = model or config.POLL_MODEL
    agents = load_agents()
    if poll_all:
        chosen = agents
    else:
        k = min(sample or config.DEFAULT_POLL_SAMPLE, len(agents))
        chosen = random.Random(seed).sample(agents, k)

    votes = collect_votes(chosen, question, options, model)
    report = _aggregate(votes, options, question)
    _save(report, question)
    _print(report)
    return report


def collect_votes(chosen, question: str, options: list[str], model: str) -> list[dict]:
    """Return individual responses for an explicitly selected cohort."""
    schema = _vote_schema(options)
    prompt = _question_prompt(question, options)

    print(f"Polling {len(chosen):,} agents with {model} ...")
    print(f"  est. cost ≈ ${estimate_cost(len(chosen), model):.2f} (batch pricing)\n")

    client = anthropic.Anthropic()

    # Build one batch request per agent. The cached CITY_CONTEXT prefix means
    # we pay full price for it ~once and cache-read it for the rest.
    requests = []
    for a in chosen:
        requests.append({
            "custom_id": a["id"],
            "params": {
                "model": model,
                "max_tokens": config.MAX_TOKENS_PER_VOTE,
                "system": build_system_blocks(a),
                "messages": [{"role": "user", "content": prompt}],
                "output_config": {"format": {"type": "json_schema", "schema": schema}},
            },
        })

    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}  (most finish within an hour)")

    # Poll until done.
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        done = batch.request_counts.succeeded + batch.request_counts.errored
        print(f"  ...{batch.processing_status}: {done:,}/{len(chosen):,}", end="\r")
        time.sleep(20)
    print("\nBatch complete. Collecting votes...\n")

    by_id = {a["id"]: a for a in chosen}
    votes = []
    for result in client.messages.batches.results(batch.id):
        if result.result.type != "succeeded":
            continue
        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "")
        vote = _parse_vote(text, options)
        if vote is None:
            continue
        agent = by_id.get(result.custom_id, {})
        votes.append({**vote, "agent": agent})

    return votes


def _parse_vote(text: str, options: list[str]) -> dict | None:
    """Parse the structured JSON; fall back to leniently extracting an object."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    choice = data.get("choice")
    if choice not in options:
        # snap to the closest option by case-insensitive match
        for o in options:
            if isinstance(choice, str) and o.lower() in choice.lower():
                choice = o
                break
        else:
            return None
    return {"choice": choice, "confidence": data.get("confidence", 3),
            "reason": data.get("reason", "")}


# --- aggregation + weighting ----------------------------------------------
def _aggregate(votes: list[dict], options: list[str], question: str) -> dict:
    total_w = sum(v["agent"].get("weight", 1.0) for v in votes) or 1.0
    tally = defaultdict(float)
    for v in votes:
        tally[v["choice"]] += v["agent"].get("weight", 1.0)

    overall = {o: {"share": tally[o] / total_w, "weighted": round(tally[o], 1)}
               for o in options}

    # Cross-tabs that are useful for messaging/targeting.
    crosstabs = {}
    for dim in ("district", "party_lean", "age_band", "housing"):
        grp = defaultdict(lambda: defaultdict(float))
        for v in votes:
            g = v["agent"].get(dim, "?")
            grp[g][v["choice"]] += v["agent"].get("weight", 1.0)
        crosstabs[dim] = {
            g: {o: round(cnt[o] / (sum(cnt.values()) or 1), 3) for o in options}
            for g, cnt in grp.items()
        }

    # A few sample verbatims per option (great for understanding the "why").
    verbatims = defaultdict(list)
    for v in votes:
        if len(verbatims[v["choice"]]) < 3 and v["reason"]:
            verbatims[v["choice"]].append(v["reason"])

    return {
        "question": question,
        "options": options,
        "n_responses": len(votes),
        "overall": overall,
        "crosstabs": crosstabs,
        "verbatims": dict(verbatims),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def _save(report: dict, question: str) -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", question.lower())[:40].strip("-")
    path = config.RESULTS_DIR / f"poll-{slug}-{int(time.time())}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Saved full results -> {path}\n")


def _print(report: dict) -> None:
    print("=" * 60)
    print(report["question"])
    print(f"(n = {report['n_responses']:,} weighted synthetic voters)")
    print("=" * 60)
    ranked = sorted(report["overall"].items(), key=lambda kv: -kv[1]["share"])
    for opt, d in ranked:
        bar = "█" * round(d["share"] * 40)
        print(f"  {opt:<22} {d['share']:6.1%} {bar}")
    print("\nWhy (sample verbatims):")
    for opt, reasons in report["verbatims"].items():
        print(f"  [{opt}]")
        for r in reasons:
            print(f"     - {r}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Poll the synthetic Malé electorate.")
    ap.add_argument("question")
    ap.add_argument("options", nargs="+", help="Two or more answer options.")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--all", action="store_true", help="Poll the whole population.")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    if len(args.options) < 2:
        ap.error("Give at least two options.")
    run_poll(args.question, args.options, sample=args.sample,
             model=args.model, poll_all=args.all)


if __name__ == "__main__":
    main()
