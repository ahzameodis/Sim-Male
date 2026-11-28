import json
import unittest
from pathlib import Path
from unittest.mock import patch

from sim_male import council_backtest as election


class CouncilTest(unittest.TestCase):
    def test_official_data_reconciles(self):
        totals = election.read_csv(election.OFFICIAL / "totals.csv")
        votes = election.read_csv(election.OFFICIAL / "votes.csv")
        self.assertEqual(len(votes), 57)
        self.assertEqual(len(totals), 18)
        register = election.read_csv(election.INPUTS / "register.csv")
        registered = {r["contest"]: int(r["registered"]) for r in register}
        self.assertEqual(set(registered), {f"T{i}" for i in range(1, 18)})
        self.assertEqual(sum(registered.values()), 58169)
        for row in totals:
            code, valid = row["contest"], int(row["valid"])
            self.assertEqual(int(row["eligible"]), 58169 if code == "T-M" else registered[code])
            results = [r for r in votes if r["contest"] == code]
            options = election.ballot(code)
            self.assertCountEqual(options, [r["number"] for r in results])
            shares = {r["number"]: int(r["votes"]) / valid for r in results}
            self.assertAlmostEqual(sum(shares.values()), 1)
            self.assertEqual(valid + int(row["invalid"]), int(row["ballots"]))
            for r in results:
                self.assertAlmostEqual(float(r["published_pct"].rstrip("%")),
                                       100 * shares[r["number"]], delta=0.005)
            grade = election.score(dict(contest=code, shares=shares,
                                        turnout=int(row["voters"]) / int(row["eligible"])))
            self.assertTrue(grade["winner_correct"])
            self.assertEqual(grade["candidate_mae_pp"], 0)
            self.assertEqual(grade["turnout_error_pp"], 0)

    def test_forecasts_run_without_2026_outcomes(self):
        register = election.read_csv(election.INPUTS / "register.csv")
        pop = [{"district": d, "party_lean": "MDP"}
               for d in sorted({r["synthetic_district"] for r in register}) for _ in range(400)]
        with patch.object(election, "OFFICIAL", Path("/nonexistent/results")):
            baseline = election.baseline()
            council = election.simulate_council(pop, 42)
            self.assertEqual(council, election.simulate_council(pop, 42))
            self.assertEqual(sum(f["synthetic_electors"] for f in council["forecasts"]), len(pop))
            forecast = election.simulate(pop, 42)
        self.assertEqual(forecast["shares"]["3"], 1)
        self.assertTrue(election.score(baseline)["winner_correct"])
        self.assertEqual(election.score_council(council["forecasts"])["seat_count"], 17)
        with self.assertRaises(ValueError):
            election.score_council(council["forecasts"][:-1])

    def test_archived_mayoral_run_and_bad_forecast(self):
        run = json.loads((election.ROOT / "runs" / "party-lean-42.json").read_text())
        grade = election.score(run)
        self.assertFalse(grade["winner_correct"])
        self.assertAlmostEqual(grade["candidate_mae_pp"], 8.00, places=2)
        run["shares"].pop("2")
        with self.assertRaises(ValueError):
            election.score(run)
