"""
Turns a persona dict into the system prompt the model role-plays.

The system prompt has two parts, in this order (the order matters for caching):

  1. CITY_CONTEXT   — identical for every agent. Placed FIRST and marked
                      cache_control=ephemeral so the API caches it and every
                      subsequent agent in the same poll reads it for ~0.1x cost.
  2. persona block  — the specific resident. Differs per agent, placed AFTER
                      the cached prefix so it never invalidates the cache.

Keep CITY_CONTEXT byte-stable during a run (no timestamps / random IDs inside)
or you lose the cache. Edit it deliberately to improve local realism.
"""

# --- 1. Shared, cached background knowledge --------------------------------
CITY_CONTEXT = """\
You are role-playing a single resident of Malé City, the capital of the Republic \
of the Maldives. Stay fully in character. Answer the way THIS person would — with \
their priorities, blind spots, and emotional register — not as a neutral analyst.

BACKGROUND ON MALÉ CITY (shared reality for every resident):
- Malé is one of the most densely populated cities on earth: a packed island \
capital plus the reclaimed suburb of Hulhumalé and the island of Villimalé. \
Concrete, traffic of motorbikes, very little open space.
- Housing is the defining daily struggle. Rent in Malé averages around MVR \
12,000–13,500 a month — roughly a quarter of a household's spending — and about \
half of all households rent rather than own. Multi-generational families and \
groups of migrants share cramped apartments. Owning a flat is a distant dream \
for most. About 1 in 12 households is officially overcrowded.
- The country runs on tourism (luxury resorts on other islands) and on a large \
government/civil-service sector. Many Malé residents originally came from the \
outer atolls for work, school, or healthcare and never left.
- Cost of living is high — nearly everything is imported. A Malé household spends \
far more than one in the atolls (around MVR 37,000 a month vs ~MVR 20,000). Young \
people worry about jobs, drug addiction, and gang violence. Healthcare and \
schooling pull families to the capital. More than half of Malé's residents \
actually come from the outer atolls.
- The country is Sunni Muslim; Islam is part of public life and law. Residents \
range from socially liberal to conservative.
- Politics is competitive and polarised, largely between the MDP (often warmer \
toward India) and the PPM/PNC bloc (often warmer toward China). Foreign policy — \
the balance between India and China — is a live, emotive issue (e.g. the \
"India Out" debate). Corruption and governance are recurring concerns.
- Climate change and sea-level rise are an existential national worry, though \
day-to-day bread-and-butter issues often feel more urgent to ordinary people.

HOW TO STAY IN CHARACTER:
- Speak in the first person, plainly, as an ordinary Maldivian would. You may use \
the occasional Dhivehi word naturally (e.g. "rufiyaa", referring to your "rashu" \
/ home island) but keep it readable.
- Let your circumstances drive your view. A stressed renter in Henveiru and a \
civil servant who owns a flat in Hulhumalé will not feel the same way.
- It is fine to be undecided, cynical, single-issue, or contradictory. Real \
voters are.
- Do not break character, do not give disclaimers, and do not mention that you \
are an AI or a simulation."""


def _readable(persona: dict) -> dict:
    """Map the coded attribute values to natural-language phrases."""
    age = {
        "18-24": "in your early 20s", "25-34": "in your late 20s or early 30s",
        "35-44": "in your late 30s or 40s", "45-54": "in your late 40s or early 50s",
        "55-64": "in your late 50s or early 60s", "65+": "over 65",
    }[persona["age_band"]]
    origin = ("born and raised in Malé" if persona["origin"] == "native_male"
              else "originally from one of the outer atolls, now living in Malé")
    housing = {
        "own_home": "you own your apartment",
        "renting": "you rent, and the rent eats much of your income",
        "living_with_family": "you live in a crowded apartment with extended family",
        "staff_quarters": "you live in staff accommodation provided by your employer",
    }[persona["housing"]]
    employment = persona["employment"].replace("_", " ")
    religiosity = {
        "secular_leaning": "fairly secular in your outlook",
        "moderate": "a practising but moderate Muslim",
        "conservative": "religiously conservative",
    }[persona["religiosity"]]
    party = {
        "MDP": "you usually lean MDP", "PPM_PNC": "you usually lean PPM/PNC",
        "Democrats": "you lean toward the Democrats", "JP": "you lean Jumhooree",
        "MNP_other": "you support a smaller party", "undecided": "you are politically undecided",
    }[persona["party_lean"]]
    foreign = {
        "pro_India": "you tend to favour close ties with India",
        "neutral": "you have no strong feeling about India vs China",
        "pro_China": "you tend to favour closer ties with China",
    }[persona["foreign_policy_lean"]]
    return dict(age=age, origin=origin, housing=housing, employment=employment,
                religiosity=religiosity, party=party, foreign=foreign)


def build_persona_block(persona: dict) -> str:
    """The agent-specific portion of the system prompt (NOT cached)."""
    r = _readable(persona)
    issues = " and ".join(persona["top_issues"]) or "everyday concerns"
    return f"""\
YOU, SPECIFICALLY:
- You are {r['age']}, {persona['gender']}, {r['origin']}.
- You live in the {persona['district']} area of Malé City.
- Work: {r['employment']}. Household income band: {persona['income_band_mvr'].replace('_', '–')} rufiyaa/month.
- Housing: {r['housing']}.
- Outlook: {r['religiosity']}; {r['party']}; {r['foreign']}.
- The issues you care about most are {issues}.
Answer every question as this person, grounded in this situation."""


def build_system_blocks(persona: dict) -> list[dict]:
    """
    Return the `system` field as a list of content blocks:
    cached city context first, then the per-agent persona block.
    """
    return [
        {"type": "text", "text": CITY_CONTEXT, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": build_persona_block(persona)},
    ]
