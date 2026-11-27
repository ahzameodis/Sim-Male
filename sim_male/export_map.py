"""
Export the seeded population as GeoJSON so you can drop it onto a map.

Run:
    python -m sim_male.export_map

Output: data/agents.geojson
Open it directly at https://geojson.io, or load it into Leaflet / Mapbox /
kepler.gl. Each point carries the agent's attributes, so you can colour dots by
party_lean, housing, age_band, etc. and literally watch the city's makeup.

(For 10k points GeoJSON is fine. For much larger runs, prefer CSV + a tiling
layer like deck.gl.)
"""

import json

from . import config
from .seed import load_agents


def export(out_path=config.DATA_DIR / "agents.geojson") -> None:
    agents = load_agents()
    features = []
    for a in agents:
        props = {k: v for k, v in a.items() if k not in ("lat", "lon")}
        props["top_issues"] = ", ".join(a.get("top_issues", []))
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [a["lon"], a["lat"]]},
            "properties": props,
        })
    fc = {"type": "FeatureCollection", "features": features}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"Wrote {len(features):,} points -> {out_path}")
    print("Open it at https://geojson.io or load into Leaflet/Mapbox/kepler.gl.")


if __name__ == "__main__":
    export()
