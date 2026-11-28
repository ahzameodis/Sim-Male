# Malé City local council election, 4 April 2026

This retrospective compares a historical benchmark and Sim-Malé's 10,000 synthetic electors with the Elections Commission's final declarations for the mayor and the 17 city council members.

## Mayor

Shares below are percentages of valid votes. Turnout uses all registered electors.

| Candidate | Official votes | Official share | 2024 baseline | Simulated, seed 42 |
|---|---:|---:|---:|---:|
| Ahmed Aiham Mohamed (independent) | 893 | 2.90% | 8.54% | 8.40% |
| Ismail Zariyand (independent) | 6,302 | 20.44% | 8.54% | 7.98% |
| Adam Azim (MDP) | 13,908 | 45.11% | 44.81% | 37.58% |
| Moosa Ali Jaleel (PNC) | 9,380 | 30.42% | 29.58% | 37.84% |
| Abdulla Mahzoom Majid (MDA) | 348 | 1.13% | 8.54% | 8.21% |
| **Turnout** | **32,948 of 58,169** | **56.64%** | **31.84%** | **32.00%** |

The five candidates received 30,831 votes in total. A further 2,117 ballots were invalid. Adam Azim's winning margin was 4,528 votes. The baseline picked Azim and missed individual shares by 5.22 percentage points on average. The synthetic vote put Jaleel first by 0.26 points and missed by 8.00 points on average. Repeating the mayoral run with voting seeds 7 and 2026 also put Jaleel first.

## Council constituencies

The baseline picked MDP in all 17 seats and got 15 winners right. The synthetic vote picked four winners correctly at seed 42. Its candidate shares were closer overall, with a mean absolute error of 6.66 percentage points versus 8.79 for the baseline. Each seat has equal weight in this metric, and within each seat every candidate has equal weight.

Repeating the same experiment with voting and constituency-assignment seeds 0 through 49, while keeping the synthetic population fixed, gave 4 to 11 correct seats (mean 7.4 of 17). Across the same 50 seeds, the citywide simulation picked Azim 11 times. This spread measures sensitivity to the random draws within this model.

| EC code | Constituency | Registered | Elected | Simulated, seed 42 |
|---|---|---:|---|---|
| T1 | Hulhumalé Dhekunu | 3,652 | MDP | PNC |
| T2 | Medhu Henveiru | 3,154 | MDP | PNC |
| T3 | Henveiru Dhekunu | 2,811 | MDP | MDP |
| T4 | Henveiru Uthuru | 2,489 | MDP | MDP |
| T5 | Galolhu Uthuru | 4,041 | MDP | PNC |
| T6 | Galolhu Dhekunu | 4,242 | MDP | PNC |
| T7 | Machangolhi Uthuru | 2,953 | MDP | MDP |
| T8 | Machangolhi Dhekunu | 2,817 | MDP | PNC |
| T9 | Maafannu Uthuru | 4,017 | MDP | PNC |
| T10 | Maafannu Hulhangu | 3,699 | MDP | MDP |
| T11 | Maafannu Medhu | 3,862 | MDP | PNC |
| T12 | Maafannu Dhekunu | 3,043 | MDP | PNC |
| T13 | Villimalé | 3,264 | PNC | MDP |
| T14 | Henveiru Hulhangu | 2,912 | MDP | PNC |
| T15 | Machangolhi Medhu | 2,942 | MDP | PNC |
| T16 | Hulhumalé Medhu | 4,166 | PNC | MDP |
| T17 | Hulhumalé Uthuru | 4,105 | MDP | PNC |

## Inputs and assumptions

- The EC ballot notice provides official Dhivehi contest titles, candidate numbers, names and affiliations. The candidate key combines constituency and ballot number. English place names follow the EC register. [Candidate notice](https://www.gazette.gov.mv/iulaan/381223)
- The 17 final constituency registers supply the electorate sizes in [register.csv](inputs/register.csv). Each count comes from the voter entries in that constituency's PDF. The counts reconcile with the eligible totals in all 17 declarations and sum to 58,169. The repository stores aggregate counts and source links. [EC register index](https://www.elections.gov.mv/en/elections/voterslist/27?kind=Constituency&page=5)
- The historical baseline carries forward the 2024 citywide mayoral MDP and PNC shares and turnout. It splits the remaining valid votes equally among the other candidates on each ballot. A two-candidate ballot uses the relative MDP and PNC shares. Applying a citywide mayoral by-election to a regular council election assumes the same underlying party support and participation everywhere. [2024 EC declaration](https://www.gazette.gov.mv/iulaan/272825)
- The synthetic vote gives every agent the 2024 turnout and invalid-ballot probabilities. Agents leaning MDP or PPM/PNC choose their party's candidate. All other agents choose uniformly among ballot candidates. The model has no candidate-specific support estimates, which matters particularly for the two independent mayoral candidates.
- For the council run, each agent draws one constituency within its existing broad district with probability proportional to registered electors. This preserves the project's broad-ward population mix. The seat allocation is statistical. It cannot locate a particular agent inside an official constituency boundary. The mayoral simulation uses the whole synthetic electorate directly.
- Only the scorer reads the 2026 declared outcomes. Candidate error is simulated share minus official share, in percentage points. The scorer reports mean absolute candidate error, turnout error, winner agreement and error in the size of the top-two margin. The declarations were already public when these rules were written. [EC mayoral declaration](https://www.gazette.gov.mv/iulaan/389096) · [All 18 declaration links](official/totals.csv) · [Candidate results](official/votes.csv)

## Reproduce

From the repository root, install the project requirements, then run:

```sh
python -m sim_male.seed --n 10000 --seed 42
python -m sim_male.council_backtest baseline > mayor-baseline.json
python -m sim_male.council_backtest simulate data/agents.jsonl --seed 42 > mayor.json
python -m sim_male.council_backtest baseline-council > council-baseline.json
python -m sim_male.council_backtest simulate-council data/agents.jsonl --seed 42 > council.json
python -m sim_male.council_backtest score mayor.json
python -m sim_male.council_backtest score council.json
python -m unittest discover -s tests
```

Any saved forecast in [runs](runs) can also be scored directly. To score another model on an individual seat, supply JSON with the EC contest code, a turnout proportion and a `shares` object keyed by the published candidate numbers. Shares must sum to one. Keep the 2026 declarations for evaluation when developing alternative rules. A next benchmark would use turnout from a previous regular council election and constituency-level party returns where boundaries can be matched.
