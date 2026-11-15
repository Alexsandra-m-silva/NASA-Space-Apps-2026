"""Time series for the Floresta compare-and-explain test.

Saves the September MODIS green channel and the NISAR browse green channel
on the same 0.01 degree grid as the GeoTIFF, plus the POWER point series.
The radar values are the public preview, not gamma0 in dB.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from rasterio.features import rasterize
from rasterio.transform import Affine

import municipality_trends as trends
import trend_geotiff as cubes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "products" / "floresta_compare.npz"
PLACE = next(item for item in trends.PLACES if item["slug"] == "floresta")


def _dates(place: dict):
    polygon = trends._municipality(place)
    west, south, east, north = polygon.bounds
    bbox = (west, south, east, north)
    width = max(1, math.ceil((east - west) / cubes.RESOLUTION))
    height = max(1, math.ceil((north - south) / cubes.RESOLUTION))
    transform = Affine(cubes.RESOLUTION, 0.0, west, 0.0, -cubes.RESOLUTION, north)
    inside = rasterize([(polygon, 1)], out_shape=(height, width), transform=transform, fill=0, dtype=np.uint8).astype(bool)

    modis = []
    for year in trends.MODIS_YEARS:
        rgb, src_transform = cubes._scene(
            bbox, trends.MODIS_LAYER, f"{year}-09-01", trends.MODIS_ZOOM, "GoogleMapsCompatible_Level7", False
        )
        keep = trends._inside(bbox, rgb.shape[0], rgb.shape[1], trends.MODIS_ZOOM, polygon)
        cloud = rgb.min(axis=2) > 190
        green = np.where(keep & ~cloud, rgb[:, :, 1].astype(np.float32), np.nan)
        grid = cubes._on_grid(green, src_transform, (height, width), transform)
        modis.append(np.where(inside & (grid != cubes.NODATA), grid, np.nan))

    nisar = []
    for day in place["nisar_dates"]:
        rgb, src_transform = cubes._scene(
            bbox, trends.NISAR_LAYER, day, trends.NISAR_ZOOM, "GoogleMapsCompatible_Level13", True
        )
        keep = trends._inside(bbox, rgb.shape[0], rgb.shape[1], trends.NISAR_ZOOM, polygon)
        colored = keep & trends._colored(rgb)
        green = np.where(colored, rgb[:, :, 1].astype(np.float32), np.nan)
        grid = cubes._on_grid(green, src_transform, (height, width), transform)
        nisar.append(np.where(inside & (grid != cubes.NODATA), grid, np.nan))

    point = polygon.representative_point()
    climate = trends.rain_report(place, float(point.x), float(point.y))
    return {
        "modis": np.stack(modis).astype(np.float32),
        "nisar": np.stack(nisar).astype(np.float32),
        "modis_years": np.array(trends.MODIS_YEARS),
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "resolution": cubes.RESOLUTION,
        "climate": climate,
        "point": (float(point.x), float(point.y)),
    }


def main() -> None:
    built = _dates(PLACE)
    climate = built.pop("climate")
    point = built.pop("point")
    np.savez_compressed(OUT, **{key: value for key, value in built.items()})
    (OUT.with_suffix(".json")).write_text(
        json.dumps(
            {
                "place": "Floresta, PE",
                "orbit": PLACE["orbit"],
                "nisar_dates": PLACE["nisar_dates"],
                "climate_point": [round(point[0], 5), round(point[1], 5)],
                "annual": climate["annual"],
                "september": climate["september"],
                "slopes": climate["slopes"],
            },
            indent=2,
        )
    )
    print("wrote", OUT, built["modis"].shape, built["nisar"].shape)


if __name__ == "__main__":
    main()
