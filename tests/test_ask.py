import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sim_male import ask
from sim_male.seed import generate


class AskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.population = generate(150, 42, Path(tmp) / "agents.jsonl")

    def test_cohort_selection_and_replay(self):
        data = ask.build(self.population, 28, 9)
        chosen = random.Random(9).sample(self.population, 28)
        self.assertEqual([a["id"] for a in chosen], [r["id"] for r in data["rows"]])
        self.assertEqual([ask.demo_pair(a) for a in chosen], [r["answers"] for r in data["rows"]])
        self.assertEqual(sum(data["counts"].values()), len(self.population))
        self.assertEqual(set(data["counts"]), set(ask.AREAS))

    def test_legacy_coordinate_is_fixed_without_changing_source(self):
        old = dict(self.population[0], lat=0, lon=0)
        row = ask.build([old], 5, 1)["rows"][0]
        self.assertGreater(row["lat"], 4)
        self.assertEqual(old["lat"], 0)

    @patch("sim_male.poll.collect_votes")
    def test_live_batches_pair_by_id_and_reject_missing_votes(self, collect):
        people = self.population[:2]
        def responses(group, question, options, model):
            return [{"agent": a, "choice": "Support", "reason": a["id"]} for a in reversed(group)]
        collect.side_effect = responses
        answers = ask.live_pairs(people, "test-model")
        self.assertEqual(collect.call_count, 2)
        self.assertEqual(answers[people[0]["id"]], [["Support", people[0]["id"]]] * 2)
        collect.side_effect = lambda *args: []
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            ask.live_pairs(people, "test-model")

    def test_quotes_are_safe_in_standalone_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"preview.html"
            ask.render({"question": "</script><script>unsafe()</script>"},path)
            self.assertNotIn("<script>unsafe()",path.read_text())
