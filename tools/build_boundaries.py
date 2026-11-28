"""Rebuild the placement polygons from the three public source downloads.

Usage: python tools/build_boundaries.py WARD_LAYER.js HDC_PARCELS.zip HDX_BOUNDARIES.zip
Build dependencies: shapely>=2, pyshp>=3, pyproj>=3.
"""
import argparse
import io
import json
from pathlib import Path
from zipfile import ZipFile

import shapefile
from pyproj import CRS, Transformer
from shapely import make_valid, set_precision, union_all
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.ops import transform

DEST = Path(__file__).resolve().parents[1] / "sim_male" / "placement.geojson"
WARD_NAMES = {"Henveyru": "Henveiru", "Galolhu": "Galolhu",
              "Maafannu": "Maafannu", "Machchangolhi": "Machchangolhi"}


def polygons(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from polygons(part)


def read_hdc(path):
    with ZipFile(path) as archive:
        stem = next(n[:-4] for n in archive.namelist() if n.endswith(".shp"))
        crs = CRS.from_wkt(archive.read(stem + ".prj").decode())
        project = Transformer.from_crs(crs, 4326, always_xy=True).transform
        parts = []
        phase2 = []
        streams = {ext: io.BytesIO(archive.read(stem + "." + ext))
                   for ext in ("shp", "shx", "dbf")}
        with shapefile.Reader(**streams) as reader:
            for record in reader.iterShapeRecords():
                attrs = record.record.as_dict()
                if attrs["landuse"] == "Residential" and attrs["status"] == "Completed":
                    parcel = make_valid(shape(record.shape.__geo_interface__))
                    parts.append(parcel)
                    if attrs["phase_no"] == "HM2":
                        phase2.append(parcel)
        return transform(project, union_all(parts)), transform(project, union_all(phase2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("wards", "parcels", "islands"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    script = args.wards.read_text(encoding="utf-8")
    wards = json.loads(script[script.index("{"):].strip().rstrip(";"))
    with ZipFile(args.islands) as archive:
        islands = {f["properties"]["adm2_pcode"]: make_valid(shape(f["geometry"]))
                   for f in json.load(archive.open("mdv_admin2.geojson"))["features"]
                   if f["properties"]["adm2_pcode"] in {"MV021001", "MV021002", "MV021003",
                                                        "MV009052", "MV009040", "MV009027"}}
    masks = {}
    for feature in wards["features"]:
        name = feature["properties"]["wardName"]
        if name in WARD_NAMES:
            masks[WARD_NAMES[name]] = make_valid(shape(feature["geometry"])).intersection(islands["MV021001"])
    masks["Villimale"] = islands["MV021002"]
    residential, phase2 = read_hdc(args.parcels)
    masks["Hulhumale"] = residential.intersection(islands["MV021003"])
    if set(masks) != set(WARD_NAMES.values()) | {"Villimale", "Hulhumale"}:
        raise ValueError("Missing a placement district")
    features = []
    for name, mask in sorted(masks.items()):
        geom = MultiPolygon(list(polygons(mask)))
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"Invalid placement geometry for {name}")
        features.append({"type": "Feature", "properties": {"district": name}, "geometry": mapping(geom)})
    DEST.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                               separators=(",", ":")) + "\n", encoding="utf-8")
    atlas = DEST.parent / "atlas"
    shorelines = [mapping(set_precision(g.simplify(.000045), .00001)) for g in islands.values()]
    (atlas / "shorelines.json").write_text(json.dumps(shorelines, separators=(",", ":")), encoding="utf-8")
    (atlas / "phase2.geojson").write_text(json.dumps(mapping(phase2), separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
