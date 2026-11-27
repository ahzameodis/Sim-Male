"""
Demographic model for Malé City — CALIBRATED TO REAL DATA.

Most distributions below are now drawn from official sources:
  - Maldives Population & Housing Census 2022 (Maldives Bureau of Statistics):
      Population, Household, Education, Employment, Unemployment & Migration
      thematic reports, and the 2022–2062 Population Projection tables.
  - Elections Commission of Maldives, Presidential Election 2023 Statistics Report
      (registered electorate, turnout, ward structure).

Each table cites its source inline. Two fields remain MODELLED ESTIMATES because
the census does not measure them (flagged ⚠️ EST):
  - INCOME_BAND_MVR  → needs the Household Income & Expenditure Survey (HIES).
  - RELIGIOSITY      → not collected (the country is constitutionally 100% Sunni).
  - PARTY_LEAN       → a prior, not an outcome. The real 2023 result lives in
                       calibration_targets.py as a VALIDATION target, deliberately
                       kept out of the prior so "predicting 2023" isn't circular.

Scope note: we model the **resident Maldivian adult (18+) electorate of Malé
City** (the 4 wards Henveiru/Galolhu/Machchangolhi/Maafannu + Hulhumalé +
Villimalé). Foreign residents (~25% of Malé's population) are excluded — they
don't vote.
"""

import random

# --- AGE (18+) -------------------------------------------------------------
# SOURCE: Population Projection 2022 base year, "Maale" sheet, Resident
# Maldivian population, single-year ages aggregated to 18+ bands.
AGE_BANDS = {
    "18-24": 0.164,
    "25-34": 0.286,
    "35-44": 0.254,
    "45-54": 0.154,
    "55-64": 0.089,
    "65+":   0.053,
}

# SOURCE: same sheet, resident Maldivian adults. Near-even, women slightly more.
GENDER = {"male": 0.495, "female": 0.505}

# --- DISTRICT / WARD -------------------------------------------------------
# SOURCE: Presidential Election 2023, registered voters by Malé City ballot box
# (total Malé City electorate = 63,346). Sub-boxes summed into the 6 wards; the
# general "Male' Rahyithun" box distributed across the 4 traditional wards.
# This is the real geographic spread of the Malé City *electorate*.
DISTRICTS = {
    "Henveiru":      0.197,
    "Galolhu":       0.123,
    "Maafannu":      0.230,
    "Machchangolhi": 0.152,
    "Hulhumale":     0.231,   # now the largest ward — huge reclaimed-land growth
    "Villimale":     0.069,
}

# --- ORIGIN (native Malé vs atoll migrant) ---------------------------------
# SOURCE: Migration Report Census 2022 — "out of the population living in Malé,
# only 46% was registered in Malé; more than half (54%) was registered in other
# atolls." Registration is the standard native/migrant proxy and is also where
# you vote.
ORIGIN = {
    "native_male": 0.46,
    "atoll_migrant": 0.54,
}

# --- EDUCATION -------------------------------------------------------------
# SOURCE: Education Census 2022, highest attainment of resident Maldivians 15+
# who ever attended (national): Primary 19.4, Secondary 41.1, Higher-sec 7.3,
# Cert/Diploma 15.7, Degree+ 10.7 (+ small pre-school/not-stated).
# Adjusted modestly upward for Malé (the capital is more educated than the
# national average; a Malé-only attainment table was not separable from the PDF).
EDUCATION = {
    "primary_or_less": 0.15,
    "secondary":       0.46,   # secondary + higher-secondary
    "diploma":         0.18,
    "bachelors":       0.14,
    "postgraduate":    0.07,
}

# --- EMPLOYMENT / PRIMARY ACTIVITY -----------------------------------------
# SOURCE: Employment Census 2022. National Maldivian-worker industry shares:
# public admin & defence 15.7%, accommodation/food 14.7%, wholesale/retail
# ~10.6%, education significant. KEY MALÉ ADJUSTMENT: the report states finance
# (86%), professional/scientific (88%), ICT (83%), real estate (95%) jobs are
# concentrated in Malé, while accommodation/food (84%) and fishing/agri (91%)
# are concentrated in the atolls/resorts. So for Malé *residents* we up-weight
# public sector + professional/retail and down-weight tourism + fishing.
# Employment-to-population ratio (national) = 60.9%; the non-employed buckets
# (student/homemaker/unemployed/retired) make up the remainder.
EMPLOYMENT = {
    "civil_service":       0.26,   # public administration, education, public health
    "private_sme":         0.18,   # professional, finance, ICT, real estate, other private
    "retail_services":     0.12,   # wholesale & retail trade
    "tourism_hospitality": 0.08,   # mostly resort-based jobs sit in the atolls
    "gig_transport":       0.05,
    "construction_trades": 0.04,   # Malé construction is heavily expatriate
    "fishing_maritime":    0.01,
    "student":             0.09,
    "homemaker":           0.10,
    "unemployed":          0.04,   # Malé unemployment rate = 5.6% of the labour force
    "retired_inactive":    0.03,
}

# --- INCOME ----------------------------------------------------------------
# SOURCE: Household Income & Expenditure Survey (HIES) 2019. Malé average
# monthly household expenditure = MVR 37,013 (vs MVR 20,177 in the atolls);
# Malé per-capita ~MVR 7,177/month; 50% of Malé households sit in the MVR
# 5,000–9,999 per-capita band and 25% above MVR 10,000. Bands below are
# household monthly income, shaped so the mean lands near the HIES Malé figure.
# NOTE: 2019 nominal MVR — adjust upward for inflation since 2019 if needed.
INCOME_BAND_MVR = {
    "under_10k": 0.06,
    "10k_20k":   0.20,
    "20k_35k":   0.31,
    "35k_60k":   0.28,
    "over_60k":  0.15,
}

# --- HOUSING ---------------------------------------------------------------
# SOURCE: Household Census 2022, Table 7 (home ownership by locality), Malé:
# Rented 49%, Owned by HH member 31%, Others 20%. (Rent fell from 59% in 2014.)
# "Others" split into living-with-family vs employer/staff quarters.
#
# Modelled CONDITIONAL ON ORIGIN: home ownership in Malé is overwhelmingly
# native-Malé families; atoll migrants almost always rent. The two distributions
# below are chosen so that, at the real 46% native / 54% migrant split, the
# weighted marginal reproduces the census (own 31%, rent 49%, family 15%,
# staff 5%) while embedding the native/migrant correlation correctly.
HOUSING = {  # overall marginal, kept for reference / reporting
    "own_home":           0.31,
    "renting":            0.49,
    "living_with_family": 0.15,
    "staff_quarters":     0.05,
}
HOUSING_BY_ORIGIN = {
    "native_male": {
        "own_home": 0.53, "renting": 0.30, "living_with_family": 0.14, "staff_quarters": 0.03,
    },
    "atoll_migrant": {
        "own_home": 0.12, "renting": 0.65, "living_with_family": 0.16, "staff_quarters": 0.07,
    },
}

# --- RELIGIOSITY -----------------------------------------------------------
# ⚠️ EST: not measured (constitutionally 100% Sunni Muslim). This models the
# social/political liberal–conservative spectrum, not faith. Replace if you find
# attitudinal survey data (e.g. Asia Foundation / Transparency Maldives polls).
RELIGIOSITY = {
    "secular_leaning": 0.22,
    "moderate":        0.55,
    "conservative":    0.23,
}

# --- PARTY LEAN ------------------------------------------------------------
# ⚠️ PRIOR, NOT OUTCOME. This is party *affiliation* with a large undecided
# bloc — deliberately NOT set equal to the 2023 vote so the model can be
# validated against that result (see calibration_targets.py). Shape informed by
# the competitive MDP vs PPM/PNC landscape of recent Malé cycles.
PARTY_LEAN = {
    "MDP":       0.29,   # Maldivian Democratic Party (often pro-India)
    "PPM_PNC":   0.30,   # Progressive / People's National Congress (often pro-China)
    "Democrats": 0.05,   # MDP splinter
    "JP":        0.03,   # Jumhooree Party
    "MNP_other": 0.05,
    "undecided": 0.28,
}

# Top issues the electorate cares about (used to flavour each persona).
ISSUE_SALIENCE = [
    "housing and overcrowding",
    "cost of living",
    "youth drug abuse and gangs",
    "jobs and the economy",
    "healthcare access",
    "climate change and sea-level rise",
    "corruption and governance",
    "religious and social policy",
    "foreign policy: India vs China",
    "waste management and environment",
]


def _weighted_choice(rng: random.Random, table: dict[str, float]) -> str:
    keys = list(table.keys())
    weights = list(table.values())
    return rng.choices(keys, weights=weights, k=1)[0]


def sample_persona(rng: random.Random, idx: int) -> dict:
    """Draw one synthetic Malé voter as a plain dict of attributes."""
    age_band = _weighted_choice(rng, AGE_BANDS)
    gender = _weighted_choice(rng, GENDER)
    district = _weighted_choice(rng, DISTRICTS)
    origin = _weighted_choice(rng, ORIGIN)
    education = _weighted_choice(rng, EDUCATION)
    employment = _weighted_choice(rng, EMPLOYMENT)
    income = _weighted_choice(rng, INCOME_BAND_MVR)
    religiosity = _weighted_choice(rng, RELIGIOSITY)
    party = _weighted_choice(rng, PARTY_LEAN)

    # --- light, defensible correlations -----------------------------------
    # INCOME is HOUSEHOLD income, so non-earners (students, homemakers) are NOT
    # forced low — they live in households with earners. We only nudge by
    # education, and keep it roughly symmetric so the HIES Malé mean is preserved.
    if education in ("bachelors", "postgraduate") and rng.random() < 0.5:
        income = rng.choices(["35k_60k", "over_60k"], [0.6, 0.4])[0]
    elif education == "primary_or_less" and rng.random() < 0.5:
        income = rng.choices(["under_10k", "10k_20k"], [0.4, 0.6])[0]

    # Housing depends on origin (natives own, migrants rent) — this reproduces
    # the census marginal while embedding the correlation. See HOUSING_BY_ORIGIN.
    housing = _weighted_choice(rng, HOUSING_BY_ORIGIN[origin])

    # Foreign-policy lean tracks party, but with noise (it's not deterministic).
    if party == "MDP":
        foreign = rng.choices(["pro_India", "neutral", "pro_China"], [0.55, 0.30, 0.15])[0]
    elif party == "PPM_PNC":
        foreign = rng.choices(["pro_India", "neutral", "pro_China"], [0.15, 0.30, 0.55])[0]
    else:
        foreign = rng.choices(["pro_India", "neutral", "pro_China"], [0.30, 0.45, 0.25])[0]

    # Each voter has one or two issues they care most about, nudged by situation.
    salience = list(ISSUE_SALIENCE)
    weights = [1.0] * len(salience)
    def bump(issue, factor):
        if issue in salience:
            weights[salience.index(issue)] *= factor
    if housing in ("renting", "living_with_family", "staff_quarters"):
        bump("housing and overcrowding", 3.0)
    if income in ("under_10k", "10k_20k"):
        bump("cost of living", 2.5)
    if age_band in ("18-24", "25-34"):
        bump("youth drug abuse and gangs", 2.0)
        bump("jobs and the economy", 1.8)
    if religiosity == "conservative":
        bump("religious and social policy", 2.5)
    top_issues = rng.choices(salience, weights=weights, k=2)
    top_issues = list(dict.fromkeys(top_issues))  # dedupe, keep order

    return {
        "id": f"male-{idx:06d}",
        "age_band": age_band,
        "gender": gender,
        "district": district,
        "origin": origin,
        "education": education,
        "employment": employment,
        "income_band_mvr": income,
        "housing": housing,
        "religiosity": religiosity,
        "party_lean": party,
        "foreign_policy_lean": foreign,
        "top_issues": top_issues,
        # weight = how much this agent counts in aggregation. Start at 1.0;
        # calibrate.py adjusts it against real marginals / poll targets.
        "weight": 1.0,
    }
