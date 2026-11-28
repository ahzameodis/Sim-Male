import json
import random
import unittest
from pathlib import Path

from shapely.geometry import Point, shape

from sim_male.demographics import DISTRICTS
from sim_male.map_data import assign_coordinates


class PlacementTest(unittest.TestCase):
    def test_all_districts_keep_points_inside_and_preserve_persona_stream(self):
        source = Path(__file__).resolve().parents[1] / "sim_male" / "placement.geojson"
        masks = {f["properties"]["district"]: shape(f["geometry"])
                 for f in json.loads(source.read_text(encoding="utf-8"))["features"]}
        self.assertEqual(set(masks), set(DISTRICTS))
        rng = random.Random(42)
        reference = random.Random(42)
        for district, mask in masks.items():
            for _ in range(100):
                lat, lon = assign_coordinates(rng, district)
                self.assertTrue(mask.contains(Point(lon, lat)), district)
                reference.random()
                reference.random()
        self.assertEqual(rng.getstate(), reference.getstate())

    def test_unknown_district_fails(self):
        with self.assertRaises(KeyError):
            assign_coordinates(random.Random(42), "unknown")
