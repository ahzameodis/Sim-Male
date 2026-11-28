"""Place synthetic voters inside the polygons documented in the project README."""
import json
import random
from bisect import bisect
from functools import lru_cache
from itertools import accumulate
from pathlib import Path

from shapely import contains_xy, prepare
from shapely.geometry import shape


@lru_cache(maxsize=1)
def _districts():
    features = json.loads(Path(__file__).with_name("placement.geojson").read_text(encoding="utf-8"))["features"]
    districts = {}
    for feature in features:
        parts = list(shape(feature["geometry"]).geoms)
        # Weight proposals by bounding-box area. Rejecting outside points then
        # gives each unit of polygon area the same chance, including on islands.
        bounds = [part.bounds for part in parts]
        weights = list(accumulate((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in bounds))
        for part in parts:
            prepare(part)
        districts[feature["properties"]["district"]] = (parts, bounds, weights)
    return districts


def assign_coordinates(rng: random.Random, district: str) -> tuple[float, float]:
    """Return (latitude, longitude) strictly inside the named district mask."""
    parts, bounds, weights = _districts()[district]
    # Earlier runs consumed two draws per resident. A private stream lets polygon
    # rejection take extra attempts without changing subsequent voters' profiles.
    local = random.Random(f"{rng.random().hex()}/{rng.random().hex()}")
    while True:
        i = bisect(weights, local.random() * weights[-1], hi=len(weights) - 1)
        west, south, east, north = bounds[i]
        lon = round(local.uniform(west, east), 7)
        lat = round(local.uniform(south, north), 7)
        if contains_xy(parts[i], lon, lat):
            return lat, lon
