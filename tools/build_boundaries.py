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
from shapely import make_valid, union_all
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
        streams = {ext: io.BytesIO(archive.read(stem + "." + ext))
                   for ext in ("shp", "shx", "dbf")}
        with shapefile.Reader(**streams) as reader:
            for record in reader.iterShapeRecords():
                attrs = record.record.as_dict()
                if attrs["landuse"] == "Residential" and attrs["status"] == "Completed":
                    parts.append(make_valid(shape(record.shape.__geo_interface__)))
        return transform(project, union_all(parts))


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
                   if f["properties"]["adm1_pcode"] == "MV021"}
    masks = {}
    for feature in wards["features"]:
        name = feature["properties"]["wardName"]
        if name in WARD_NAMES:
            masks[WARD_NAMES[name]] = make_valid(shape(feature["geometry"])).intersection(islands["MV021001"])
    masks["Villimale"] = islands["MV021002"]
    masks["Hulhumale"] = read_hdc(args.parcels).intersection(islands["MV021003"])
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


if __name__ == "__main__":
    main()
