"""Malé local election reconstruction. Forecast and scoring commands use separate inputs."""
import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "elections" / "2026-male"
INPUTS = ROOT / "inputs"
OFFICIAL = ROOT / "official"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def historical_prior():
    old = json.loads((INPUTS / "mayor_2024.json").read_text())
    return old, old["voters"] / old["eligible"]


def ballot(contest):
    rows = [r for r in read_csv(INPUTS / "ballots.csv") if r["contest"] == contest]
    if not rows:
        raise ValueError(f"Unknown contest: {contest}")
    return {r["number"]: r["affiliation"] for r in rows}


def baseline(contest="T-M"):
    options = ballot(contest)
    old, turnout = historical_prior()
    votes = old["valid_votes"]
    valid = sum(votes.values())
    # Carry forward the two comparable major parties. Allocate the residual
    # equally among all remaining candidates, including the new party entrant.
    other = [n for n, party in options.items() if party not in ("MDP", "PNC")]
    rest = valid - votes["MDP"] - votes["PNC"]
    denominator = valid if other else votes["MDP"] + votes["PNC"]
    shares = {n: (rest / len(other) if n in other else votes[party]) / denominator
              for n, party in options.items()}
    return {"contest": contest, "method": "2024 carry-forward", "turnout": turnout, "shares": shares}


def simulate(population, seed, contest="T-M"):
    options = ballot(contest)
    old, turnout = historical_prior()
    rng = random.Random(seed)
    choices = list(options)
    totals = Counter()
    voted = eligible = 0.0
    n = 0
    for agent in population:
        weight = float(agent.get("weight", 1))
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("Voter weights must be finite and positive")
        n += 1
        eligible += weight
        if rng.random() >= turnout:
            continue
        voted += weight
        if rng.random() < old["invalid"] / old["voters"]:
            continue
        party = {"MDP": "MDP", "PPM_PNC": "PNC"}.get(agent["party_lean"])
        matches = [n for n in choices if options[n] == party]
        totals[rng.choice(matches or choices)] += weight
    valid = sum(totals.values())
    if not valid:
        raise ValueError("No valid synthetic votes")
    return {"contest": contest, "method": "party-lean rule v1", "seed": seed,
            "synthetic_electors": n, "turnout": voted / eligible,
            "shares": {n: totals[n] / valid for n in choices}}


def simulate_council(population, seed):
    """Draw one constituency per agent from the register within its broad ward."""
    by_ward = defaultdict(list)
    registers = read_csv(INPUTS / "register.csv")
    for row in registers:
        by_ward[row["synthetic_district"]].append(row)
    assignment_rng = random.Random(seed)
    groups = defaultdict(list)
    for agent in population:
        rows = by_ward.get(agent["district"])
        if not rows:
            raise ValueError(f"Unknown synthetic district: {agent['district']}")
        seat = assignment_rng.choices(rows, weights=[int(r["registered"]) for r in rows])[0]
        groups[seat["contest"]].append(agent)
    forecasts = []
    for row in registers:
        code = row["contest"]
        # Use a distinct, stable stream for each seat, independent of assignment.
        vote_seed = f"{seed}/{code}"
        forecasts.append(simulate(groups[code], vote_seed, code))
    return {"assignment_seed": seed, "forecasts": forecasts}


def score(forecast):
    code = forecast["contest"]
    options = ballot(code)
    shares = forecast["shares"]
    if set(shares) != set(options) or not math.isclose(sum(shares.values()), 1.0, abs_tol=1e-6):
        raise ValueError("Provide one valid-vote share per ballot option, summing to one")
    if any(not 0 <= p <= 1 for p in [*shares.values(), forecast["turnout"]]):
        raise ValueError("Shares and turnout must be probabilities")
    total = next(r for r in read_csv(OFFICIAL / "totals.csv") if r["contest"] == code)
    counts = {r["number"]: int(r["votes"]) for r in read_csv(OFFICIAL / "votes.csv") if r["contest"] == code}
    actual = {n: counts[n] / int(total["valid"]) for n in options}
    errors = {n: 100 * (shares[n] - actual[n]) for n in options}
    def margin(p):
        first, second = sorted(p.values(), reverse=True)[:2]
        return 100 * (first - second)
    return {"contest": code, "actual_shares": actual, "error_pp": errors,
            "candidate_mae_pp": sum(map(abs, errors.values())) / len(options),
            "winner_correct": {n for n in options if shares[n] == max(shares.values())}
                              == {n for n in options if actual[n] == max(actual.values())},
            "margin_error_pp": margin(shares) - margin(actual),
            "turnout_error_pp": 100 * (forecast["turnout"] - int(total["voters"]) / int(total["eligible"]))}


def score_council(forecasts):
    contests = {r["contest"] for r in read_csv(INPUTS / "register.csv")}
    if len(forecasts) != len(contests) or {f["contest"] for f in forecasts} != contests:
        raise ValueError("Provide exactly one forecast per council constituency")
    seats = [score(f) for f in forecasts]
    return {
        "seats_correct": sum(r["winner_correct"] for r in seats),
        "seat_count": len(seats),
        "mean_seat_candidate_mae_pp": sum(r["candidate_mae_pp"] for r in seats) / len(seats),
        "seats": seats,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="command", required=True)
    modes.add_parser("baseline")
    modes.add_parser("baseline-council")
    for name in ("simulate", "simulate-council"):
        sim = modes.add_parser(name)
        sim.add_argument("population", type=Path)
        sim.add_argument("--seed", type=int, default=42)
    grade = modes.add_parser("score")
    grade.add_argument("forecast", type=Path)
    args = parser.parse_args()
    if args.command == "baseline":
        report = baseline()
    elif args.command == "baseline-council":
        report = {"forecasts": [baseline(row["contest"]) for row in read_csv(INPUTS / "register.csv")]}
    elif args.command in ("simulate", "simulate-council"):
        with args.population.open(encoding="utf-8") as stream:
            population = (json.loads(line) for line in stream if line.strip())
            runner = simulate if args.command == "simulate" else simulate_council
            report = runner(population, args.seed)
    else:
        forecast = json.loads(args.forecast.read_text(encoding="utf-8"))
        report = score_council(forecast["forecasts"]) if "forecasts" in forecast else score(forecast)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
