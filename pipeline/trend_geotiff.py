"""GeoTIFF stack for each whole municipality.

This is the data product. It does not write the web map.

Bands, EPSG:4326, 0.01 degree, nodata -9999:
1. MODIS September slope, green-channel color units per year, 2016–2026
2. NISAR browse slope, green-channel units per day, one SHSH orbit in 2026
3. Decline class: 0 observed without decline, 1 MODIS, 2 NISAR, 3 both
4. Annual precipitation slope, mm/year, 2001–2025, one POWER point
5. Annual temperature slope, °C/year, 2001–2025, the same point
6. Annual precipitation slope, mm/year, 2016–2025
7. September temperature slope, °C/year, 2016–2026

Bands 4–7 repeat the municipal point on every pixel inside the polygon.
They are not a climate map. MODIS is not numeric NDVI, and NISAR is not gamma0.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject

import municipality_trends as trends

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "products"
NODATA = -9999.0
RESOLUTION = 0.01
MERCATOR_ORIGIN = 20037508.342789244

BANDS = [
    "modis_slope_per_year",
    "nisar_slope_per_day",
    "decline_class",
    "precip_mm_per_year_2001_2025",
    "temp_c_per_year_2001_2025",
    "precip_mm_per_year_2016_2025",
    "september_temp_c_per_year_2016_2026",
]


def _mercator_affine(origin: tuple[int, int], left: int, top: int, zoom: int) -> Affine:
    resolution = (2 * MERCATOR_ORIGIN) / (256 * 2**zoom)
    column = origin[0] * 256 + left
    row = origin[1] * 256 + top
    x = -MERCATOR_ORIGIN + column * resolution
    y = MERCATOR_ORIGIN - row * resolution
    return Affine(resolution, 0.0, x, 0.0, -resolution, y)


def _scene(bbox, layer: str, day: str, zoom: int, matrix: str, drop_grey: bool):
    canvas, origin = trends._mosaic(bbox, layer, day, zoom, matrix, drop_grey)
    image = trends._crop(canvas, origin, zoom, bbox)
    x0, y_north = trends._tile_frac(bbox[0], bbox[3], zoom)
    left = int(round((x0 - origin[0]) * 256))
    top = int(round((y_north - origin[1]) * 256))
    return np.asarray(image), _mercator_affine(origin, left, top, zoom)


def _on_grid(source: np.ndarray, src_transform: Affine, dst_shape: tuple[int, int], dst_transform: Affine) -> np.ndarray:
    filled = np.where(np.isfinite(source), source, NODATA).astype(np.float32)
    destination = np.full(dst_shape, NODATA, dtype=np.float32)
    reproject(
        filled,
        destination,
        src_transform=src_transform,
        src_crs="EPSG:3857",
        src_nodata=NODATA,
        dst_transform=dst_transform,
        dst_crs="EPSG:4326",
        dst_nodata=NODATA,
        resampling=Resampling.average,
    )
    return destination


def _stack(place: dict) -> tuple[np.ndarray, Affine, dict]:
    polygon = trends._municipality(place)
    west, south, east, north = polygon.bounds
    bbox = (west, south, east, north)
    width = max(1, math.ceil((east - west) / RESOLUTION))
    height = max(1, math.ceil((north - south) / RESOLUTION))
    transform = Affine(RESOLUTION, 0.0, west, 0.0, -RESOLUTION, north)
    inside = rasterize([(polygon, 1)], out_shape=(height, width), transform=transform, fill=0, dtype=np.uint8).astype(bool)
    print(place["name"], f"{width}x{height}", flush=True)

    print("MODIS", flush=True)
    modis = []
    modis_valid = []
    modis_transform = None
    for year in trends.MODIS_YEARS:
        rgb, modis_transform = _scene(
            bbox, trends.MODIS_LAYER, f"{year}-09-01", trends.MODIS_ZOOM, "GoogleMapsCompatible_Level7", False
        )
        keep = trends._inside(bbox, rgb.shape[0], rgb.shape[1], trends.MODIS_ZOOM, polygon)
        cloud = rgb.min(axis=2) > 190
        modis.append(rgb[:, :, 1].astype(np.float32))
        modis_valid.append(keep & ~cloud)
    modis_slope = trends._slope(
        np.stack(modis), np.array(trends.MODIS_YEARS, dtype=float), np.stack(modis_valid), 8
    )

    print("NISAR", flush=True)
    dates = place["nisar_dates"]
    nisar = []
    nisar_valid = []
    nisar_transform = None
    elapsed = np.array([(date.fromisoformat(day) - date.fromisoformat(dates[0])).days for day in dates], dtype=float)
    for day in dates:
        rgb, nisar_transform = _scene(
            bbox, trends.NISAR_LAYER, day, trends.NISAR_ZOOM, "GoogleMapsCompatible_Level13", True
        )
        keep = trends._inside(bbox, rgb.shape[0], rgb.shape[1], trends.NISAR_ZOOM, polygon)
        nisar.append(rgb[:, :, 1].astype(np.float32))
        nisar_valid.append(keep & trends._colored(rgb))
    nisar_slope = trends._slope(np.stack(nisar), elapsed, np.stack(nisar_valid), 4)

    modis_grid = _on_grid(modis_slope, modis_transform, (height, width), transform)
    nisar_grid = _on_grid(nisar_slope, nisar_transform, (height, width), transform)
    modis_grid = np.where(inside, modis_grid, NODATA)
    nisar_grid = np.where(inside, nisar_grid, NODATA)

    modis_obs = inside & (modis_grid != NODATA)
    nisar_obs = inside & (nisar_grid != NODATA)
    modis_down = modis_obs & (modis_grid < 0)
    nisar_down = nisar_obs & (nisar_grid < 0)
    decline = np.full((height, width), NODATA, dtype=np.float32)
    decline[modis_obs | nisar_obs] = 0
    decline[modis_down & ~nisar_down] = 1
    decline[nisar_down & ~modis_down] = 2
    decline[modis_down & nisar_down] = 3

    point = polygon.representative_point()
    climate = trends.rain_report(place, float(point.x), float(point.y))
    slopes = climate["slopes"]
    climate_values = [
        slopes["annual_precip_mm_per_year"],
        slopes["annual_temp_c_per_year"],
        slopes["modis_years_annual_precip_mm_per_year"],
        slopes["modis_years_september_temp_c_per_year"],
    ]
    bands = [modis_grid, nisar_grid, decline]
    for value in climate_values:
        layer = np.full((height, width), NODATA, dtype=np.float32)
        if value is not None:
            layer[inside] = value
        bands.append(layer)
    stack = np.stack(bands).astype(np.float32)

    summary = {
        "slug": place["slug"],
        "place": f"{place['name']}, {place['uf']}",
        "file": f"{place['slug']}.tif",
        "orbit": place["orbit"],
        "nisar_dates": dates,
        "climate_point": [round(float(point.x), 5), round(float(point.y), 5)],
        "modis_pixels": int(modis_obs.sum()),
        "nisar_pixels": int(nisar_obs.sum()),
        "class_counts": {
            "modis_only": int((decline == 1).sum()),
            "nisar_only": int((decline == 2).sum()),
            "both": int((decline == 3).sum()),
            "observed_without_decline": int((decline == 0).sum()),
        },
        "climate": slopes,
    }
    return stack, transform, summary


def _write(path: Path, stack: np.ndarray, transform: Affine, summary: dict) -> None:
    height, width = stack.shape[1:]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=stack.shape[0],
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=NODATA,
        compress="deflate",
        tiled=True,
        predictor=3,
    ) as dataset:
        dataset.write(stack)
        for index, name in enumerate(BANDS, start=1):
            dataset.set_band_description(index, name)
        dataset.update_tags(
            place=summary["place"],
            orbit=summary["orbit"],
            climate_lon=summary["climate_point"][0],
            climate_lat=summary["climate_point"][1],
            decline_class="0 sem queda, 1 so MODIS, 2 so NISAR, 3 os dois",
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summaries = []
    for place in trends.PLACES:
        stack, transform, summary = _stack(place)
        _write(OUT / summary["file"], stack, transform, summary)
        summaries.append(summary)
        print(json.dumps(summary["class_counts"]), flush=True)
    manifest = {
        "crs": "EPSG:4326",
        "resolution_deg": RESOLUTION,
        "nodata": NODATA,
        "bands": BANDS,
        "note": (
            "O MODIS é a inclinação do canal verde da paleta GIBS de setembro, não NDVI numérico. "
            "O NISAR é a prévia HV de uma órbita e uma polarização, em cerca de quatro meses de 2026, não gamma0. "
            "Chuva e temperatura são um ponto interno do município, repetido no polígono para acompanhar o raster. "
            "O registro 2001–2025 e a janela do MODIS estão em bandas separadas."
        ),
        "places": summaries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
