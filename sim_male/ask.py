"""Build the self-contained Ask Malé transit scenario from a synthetic population."""
import argparse
import json
import os
import random
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from shapely import contains_xy, prepare
from shapely.geometry import mapping, shape

from . import config
from .map_data import assign_coordinates
from .seed import generate, load_agents

HERE = Path(__file__).parent
ATLAS = HERE / "atlas"
QUESTION = "Would you support a more frequent evening bus service between Malé and Hulhumalé?"
FARE = "The fare would stay the same."
OPTIONS = ["Support", "Oppose", "Undecided"]
AREAS = ["Henveiru", "Galolhu", "Machchangolhi", "Maafannu", "Villimalé",
         "Hulhumalé · Phase 1", "Hulhumalé · Phase 2"]


def area_for(agent, phase2):
    if agent["district"] == "Hulhumale":
        return AREAS[6] if contains_xy(phase2, agent["lon"], agent["lat"]) else AREAS[5]
    return "Villimalé" if agent["district"] == "Villimale" else agent["district"]


def demo_pair(agent):
    """Illustrative templates and explicit assumed preferences, never fitted survey data."""
    rng = random.Random("evening-bus-demo-v1/" + agent["id"])
    preference = rng.random()
    fare_sensitive = rng.random() < .46
    if preference < .34:
        base = ["Support", "Shorter evening waits would make this service more useful to me."]
    elif preference < .53:
        base = ["Oppose", "I would give improving the existing daytime service priority."]
    elif fare_sensitive:
        base = ["Undecided", "I would want to know what the extra evening trips would cost me."]
    else:
        base = ["Undecided", "I would need to see the stops and the last departure time."]
    revised = base
    if base[0] == "Undecided" and fare_sensitive:
        revised = ["Support", "Keeping the same fare answers my main concern about the extra trips."]
    return [base, revised]


def live_pairs(agents, model):
    from .poll import collect_votes
    ids = {a["id"] for a in agents}
    paired = {key: [] for key in ids}
    for question in [QUESTION, QUESTION + " " + FARE]:
        votes = collect_votes(agents, question, OPTIONS, model)
        if {v["agent"]["id"] for v in votes} != ids or len(votes) != len(ids):
            raise ValueError("Incomplete paired batch. A comparison requires two responses per resident.")
        for vote in votes:
            paired[vote["agent"]["id"]].append([vote["choice"], vote["reason"]])
    return paired


def build(population, sample, seed, model=None):
    if not population or sample < 1:
        raise ValueError("A nonempty population and a positive sample size are required.")
    if len({a["id"] for a in population}) != len(population):
        raise ValueError("Resident IDs must be unique.")
    phase2 = shape(json.loads((ATLAS / "phase2.geojson").read_text()))
    prepare(phase2)
    features = json.loads((HERE / "placement.geojson").read_text())["features"]
    placement = {f["properties"]["district"]: shape(f["geometry"]) for f in features}
    for geometry in placement.values():
        prepare(geometry)
    located = []
    for agent in population:
        district = agent["district"]
        if not contains_xy(placement[district], agent["lon"], agent["lat"]):
            lat, lon = assign_coordinates(random.Random("relocate/" + agent["id"]), district)
            agent = dict(agent, lat=lat, lon=lon)
        located.append(agent)
    population = located
    areas = {a["id"]: area_for(a, phase2) for a in population}
    chosen = random.Random(seed).sample(population, min(sample, len(population)))
    answers = live_pairs(chosen, model) if model else {a["id"]: demo_pair(a) for a in chosen}
    respondents = []
    for a in chosen:
        respondents.append(dict(id=a["id"], area=areas[a["id"]], age=a["age_band"],
                                occupation=a["employment"].replace("_", " "), lon=a["lon"],
                                lat=a["lat"], weight=a.get("weight", 1), answers=answers[a["id"]]))
    masks = {}
    for d, g in placement.items():
        if d == "Hulhumale":
            masks[AREAS[5]] = g.difference(phase2)
            masks[AREAS[6]] = g.intersection(phase2)
        else:
            masks["Villimalé" if d == "Villimale" else d] = g
    return dict(question=QUESTION, fare=FARE, options=OPTIONS, areas=AREAS, n=len(population),
                counts=Counter(areas.values()), rows=respondents, seed=seed,
                method=model or "Illustrative rules v1", live=bool(model),
                date=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                shores=json.loads((ATLAS / "shorelines.json").read_text()),
                masks={k:mapping(g.simplify(.000055)) for k,g in masks.items()})


def render(data, output):
    # All inputs stay local. Escaping '<' keeps generated text inside its JSON script.
    template = (ATLAS / "index.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")
    html = template.replace("/*ASK_CSS*/", (ATLAS / "style.css").read_text(encoding="utf-8"))
    html = html.replace("/*ASK_APP*/", (ATLAS / "app.js").read_text(encoding="utf-8"))
    html = html.replace("<!--ASK_DATA-->", payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
    os.replace(f.name, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=Path, help="Existing JSONL. Default generates the standard 10,000 profiles in temporary storage.")
    parser.add_argument("--sample", type=int, default=350)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--live-model", help="Submit two paid API batches with this model. Default is the offline rule demo.")
    parser.add_argument("--output", type=Path, default=config.DATA_DIR / "ask-male.html")
    args = parser.parse_args()
    if args.live_model and (not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY","").endswith("...")):
        parser.error("A configured Anthropic API key is required for live batches.")
    with tempfile.TemporaryDirectory() as tmp:
        agents = load_agents(args.population) if args.population else generate(
            config.POPULATION_SIZE, config.RANDOM_SEED, Path(tmp) / "agents.jsonl")
    data = build(agents, args.sample, args.seed, args.live_model)
    render(data, args.output)
    print(f"Wrote {args.output} with {len(data['rows'])} paired synthetic responses ({data['method']}).")


if __name__ == "__main__":
    main()
