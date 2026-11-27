# Sim Malé 🇲🇻

An AI-driven synthetic population of **Malé City**, the capital of the Maldives —
10,000 persona-based agents placed on a map of the city, that you can poll on
issues and propositions and feed live news events to, watching reactions split
by district and party.

Inspired by "Sim Francisco" / Stanford's *Generative Agents*.

---

## ⚠️ Read this first: what this is good for

This system is a strong **qualitative scenario explorer**. It is genuinely useful for:

- understanding **how** different kinds of Malé residents frame an issue,
- finding **which arguments land** with renters in Henveiru vs. homeowners in Hulhumalé,
- pressure-testing a message or policy before it goes public,
- generating **hypotheses** about where opinion sits.

It is **not** a validated election forecaster. LLM-simulated electorates
("silicon sampling") have well-documented, systematic biases — they lean toward
whatever was common in training data and smooth over local nuance. **Treat every
percentage as a directional hypothesis, not a prediction.** The only path to
"accurate" is calibrating against real Malé polling (see [Calibration](#5-calibration-the-honest-path-to-accuracy)).

---

## Setup

```powershell
# from this folder (sim-male/)
python -m pip install -r requirements.txt

# add your Anthropic API key
copy .env.example .env
notepad .env          # paste your key from https://console.anthropic.com/
```

Python 3.10+ required.

---

## The three building blocks (your method, mapped to the code)

| Your step | Where it lives | What it does |
|---|---|---|
| **1. Persona-based system prompt** | [`sim_male/persona.py`](sim_male/persona.py) | Shared `CITY_CONTEXT` (cached) + a per-agent persona block. |
| **2. Multi-agent interaction framework** | [`sim_male/agent.py`](sim_male/agent.py) | `ask_agent()` for one resident; `AgentConversation` for focus groups. |
| **3. Seed with demographic data** | [`sim_male/demographics.py`](sim_male/demographics.py) + [`seed.py`](sim_male/seed.py) | Weighted distributions → 10,000 agents on the map. |

---

## Quick start

```powershell
# 1. Generate the 10,000-agent population (no API key needed)
python -m sim_male.seed --n 10000

# 2. Put them on a map (writes data/agents.geojson — open at geojson.io)
python -m sim_male.export_map

# 3. Cheap end-to-end demo: 3 residents + a focus group (a few cents)
python run_demo.py

# 4. A full poll of a representative sample (uses the Batch API)
python -m sim_male.poll "Who would you vote for in the next presidential election?" "MDP candidate" "PPM/PNC candidate" "Undecided"

# 5. Drop in a news event and see localized reactions
python -m sim_male.events "Government announces 4,000 new flats in Hulhumalé, ready by 2028"
```

---

## How it works

### 1. Seeding (`demographics.py` → `seed.py`)
Each agent is drawn from weighted distributions for age, district, origin
(native Malé vs atoll migrant), education, employment, income, housing,
religiosity, party lean, foreign-policy lean (India/China), and top issues —
with correlations modelled so the joint structure stays realistic (e.g. housing
is conditional on origin, so the native/migrant ownership gap is captured *and*
the overall ownership rate still matches the census). Output is one JSON object
per line in `data/agents.jsonl`, each with `lat`/`lon` inside its district.

**The distributions are calibrated to official data**, not guesses:

| Field | Source |
|---|---|
| Age (18+), sex | Census 2022 Population Projection — Malé, resident Maldivians |
| District / ward | Presidential Election 2023 — registered voters per Malé ward (63,346 total) |
| Origin (native/migrant) | Migration Report 2022 — only 46% of Malé residents are registered in Malé |
| Housing tenure | Household Census 2022 — Malé: 49% rent, 31% own, 8% overcrowded |
| Education | Education Census 2022 attainment (Malé-adjusted) |
| Employment | Employment Census 2022 (Malé-adjusted: more public sector/services, less resort tourism) |
| Income | HIES 2019 — Malé avg household ≈ MVR 37,013/mo; the model reproduces this mean |
| Party lean | Modelled prior (kept separate from the 2023 result — see Calibration) |
| Religiosity | ⚠️ Modelled estimate (not measured by the census) |

Verify after seeding — the printed marginals should match the table above.

### 2. Personas (`persona.py`)
The system prompt is two blocks: a big shared `CITY_CONTEXT` (marked for prompt
caching so you pay for it ~once per poll instead of 10,000 times) followed by the
specific resident. Keep `CITY_CONTEXT` byte-stable during a run or you lose the
cache.

### 3. Polling at scale (`poll.py`)
Fans out to a representative **sample** (default 1,500; use `--all` for all
10,000) via the **Message Batches API** — 50% cheaper and built for this. Each
agent returns a structured JSON vote (`choice`, `confidence`, `reason`), which is
then weighted and tallied with cross-tabs by district, party, age, and housing,
plus sample verbatims explaining the "why". Full results are saved to
`data/results/`.

### 4. Events (`events.py`)
Feeds a headline to a sample and collects sentiment + whether it moves their
vote, summarized by district and party.

### 5. Calibration & validation: the honest path to accuracy
Each agent carries a `weight` (default `1.0`). [`calibrate.py`](sim_male/calibrate.py)
does **post-stratification (raking)** — it adjusts weights so the weighted
population matches known real marginals:

```powershell
python -m sim_male.calibrate     # rakes weights to the real per-ward electorate
```

The real 2023 results and Malé turnout live in
[`calibration_targets.py`](sim_male/calibration_targets.py), kept **out** of the
demographic priors on purpose: party lean is a *prior*, the election result is
the *thing to predict*. Baking the result into the prior would make "predicting
2023" circular. The honest workflow:

1. **Calibrate** weights to known marginals (district, and later age/turnout).
2. **Validate** against the 2023 runoff — one command:

   ```powershell
   python -m sim_male.validate          # mock Sept-2023 runoff, scored vs reality
   ```

   It polls the electorate on the Muizzu vs Solih runoff, computes the two-party
   split among decided voters, and scores it against the real result
   (`PRES_2023_ROUND2`: Muizzu 54% / Solih 46%) — plus a turnout proxy vs Malé's
   real 82.7%, and a by-party-lean sanity table. If Sim Malé can't reproduce a
   *known* election, don't trust it on an unknown one — tune priors until it can.

   > The built-in target is the **national** result; Malé leans differently, so
   > expect a few points of gap. For a strict test, make the target Malé-specific
   > by aggregating the EC report's per-box Malé candidate tables.
3. Only then use it for forward-looking polls, still as hypotheses.

---

## Cost

Batch pricing, rough estimates (the tool prints a live estimate before running):

| Sample | Haiku 4.5 | Sonnet 4.6 |
|---|---|---|
| 1,500 | ~$1.60 | ~$4.80 |
| 10,000 | ~$10.75 | ~$32 |

`POLL_MODEL` in [`config.py`](sim_male/config.py) defaults to **Haiku 4.5** — a
deliberate cost choice for mass polling. Switch to `claude-sonnet-4-6` (richer
reasoning) or `claude-opus-4-8` (best, but ~25× Haiku) with `--model` or by
editing the config. Interactive single-agent chats use **Opus 4.8** by default.

Polling a 1,500 sample and weighting is statistically fine and ~7× cheaper than
asking all 10,000 every time.

---

## Project layout

```
sim-male/
├─ run_demo.py            # cheap end-to-end demo (no Batch API)
├─ requirements.txt
├─ .env.example
├─ sim_male/
│  ├─ config.py           # models, paths, sample sizes, pricing
│  ├─ demographics.py     # ⚠️ the distributions to replace with real census data
│  ├─ map_data.py         # district centroids → lat/lon scatter
│  ├─ persona.py          # CITY_CONTEXT + per-agent system prompt (cached)
│  ├─ seed.py             # generate population → agents.jsonl
│  ├─ agent.py            # single agent + focus-group framework
│  ├─ poll.py             # Batch-API poll + weighting + cross-tabs
│  ├─ events.py           # inject a news event, summarize reactions
│  ├─ calibrate.py        # post-stratification (raking) of agent weights
│  ├─ calibration_targets.py  # real 2023 election results + Malé turnout
│  ├─ validate.py         # score a mock 2023 runoff against the real result
│  └─ export_map.py       # agents.jsonl → agents.geojson
└─ data/                  # generated: agents.jsonl, agents.geojson, results/
```

---

## Suggested roadmap

1. **Replace the placeholder demographics** with Census 2022 + voter-registry data.
2. **Calibrate** against one real poll (post-stratification on `weight`).
3. **Validate**: hold out a known result (e.g. a past election or referendum) and
   check whether the simulation reproduces it *before* trusting new predictions.
4. **Build a UI**: a Leaflet/Mapbox map that colours the 10k dots by live poll
   choice; a panel to type a question or paste a headline.
5. **Add memory**: give agents persistent state so events accumulate over a
   campaign timeline rather than being one-shot.
```
