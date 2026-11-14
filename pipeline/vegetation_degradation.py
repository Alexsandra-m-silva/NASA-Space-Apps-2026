"""Vegetation trend for a small box in Jardim do Seridó, Rio Grande do Norte.

MODIS monthly NDVI, every September from 2016 through 2026, is the
multi-year series. The slope of that color scale is the dry-season trend.

NISAR has no earlier years. The public record on descending track 067,
frame 092, same SHSH polarization, is six passes from 30 Jun to 28 Oct 2026.
That slope is a four-month browse change, not desertification.

The green channel of the NISAR preview is not gamma0 in dB, and each
GIBS tile is stretched on its own.
"""

from __future__ import annotations

import json
import math
import time
from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
from PIL import Image
from shapely import contains_xy
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "degradation"

# About 13 km by 11 km, inside Jardim do Seridó. west, south, east, north
BBOX = (-36.84, -6.64, -36.72, -6.54)
RAIN_POINT = (-36.78, -6.59)
NISAR_ZOOM = 9
NISAR_LAYER = "NISAR_L2_Geocoded_Polarimetric_Covariance"
MODIS_ZOOM = 7
MODIS_LAYER = "MODIS_Terra_L3_NDVI_Monthly"
MODIS_YEARS = list(range(2016, 2027))
# Same descending track and SHSH polarization. Twelve-day repeats that
# switched to DHDH are left out so the slope is not a polarization change.
NISAR_DATES = [
    "2026-06-30",
    "2026-07-24",
    "2026-08-17",
    "2026-09-10",
    "2026-10-04",
    "2026-10-28",
]


def _tile_frac(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2**z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def _fetch(url: str) -> Image.Image:
    last = "empty"
    for attempt in range(5):
        try:
            data = urlopen(url, timeout=40).read()
        except Exception as exc:  # noqa: BLE001 — retry transient GIBS errors
            last = str(exc)
            time.sleep(0.6 * (attempt + 1))
            continue
        if len(data) < 500:
            last = f"short {len(data)}"
            time.sleep(0.4)
            continue
        return Image.open(BytesIO(data)).convert("RGB")
    raise RuntimeError(f"{url} {last}")


def _mosaic(layer: str, day: str, z: int, matrix: str, drop_grey: bool) -> tuple[Image.Image, tuple[int, int]]:
    x0, y_north = _tile_frac(BBOX[0], BBOX[3], z)
    x1, y_south = _tile_frac(BBOX[2], BBOX[1], z)
    xs = range(math.floor(x0), math.floor(x1) + 1)
    ys = range(math.floor(y_north), math.floor(y_south) + 1)
    canvas = Image.new("RGB", (len(xs) * 256, len(ys) * 256))
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            url = (
                "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
                f"{layer}/default/{day}/{matrix}/{z}/{y}/{x}.png"
            )
            tile = _fetch(url)
            average = np.asarray(tile).reshape(-1, 3).mean(axis=0)
            grey = abs(average[0] - average[1]) < 12 and abs(average[1] - average[2]) < 12
            if drop_grey and grey:
                tile = Image.new("RGB", tile.size)
                print(f"  {day} {z}/{y}/{x} grey, dropped")
            else:
                print(f"  {day} {z}/{y}/{x}")
            canvas.paste(tile, (ix * 256, iy * 256))
    return canvas, (math.floor(x0), math.floor(y_north))


def _crop(canvas: Image.Image, origin: tuple[int, int], z: int) -> Image.Image:
    x0, y_north = _tile_frac(BBOX[0], BBOX[3], z)
    x1, y_south = _tile_frac(BBOX[2], BBOX[1], z)
    left = int(round((x0 - origin[0]) * 256))
    right = int(round((x1 - origin[0]) * 256))
    top = int(round((y_north - origin[1]) * 256))
    bottom = int(round((y_south - origin[1]) * 256))
    return canvas.crop((left, top, right, bottom))


def _municipality():
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-24-mun.json"
    with urlopen(url, timeout=40) as response:
        data = json.load(response)
    feature = next(item for item in data["features"] if item["properties"]["name"] == "Jardim do Seridó")
    (OUT / "municipality.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}))
    return shape(feature["geometry"]).buffer(0)


def _inside(height: int, width: int, zoom: int, polygon) -> np.ndarray:
    x_west, y_north = _tile_frac(BBOX[0], BBOX[3], zoom)
    x_east, y_south = _tile_frac(BBOX[2], BBOX[1], zoom)
    cols = x_west + (np.arange(width) + 0.5) * (x_east - x_west) / width
    rows = y_north + (np.arange(height) + 0.5) * (y_south - y_north) / height
    lons = cols / (2**zoom) * 360.0 - 180.0
    lats = np.degrees(np.arctan(np.sinh(np.pi * (1.0 - 2.0 * rows / (2**zoom)))))
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return contains_xy(polygon, lon_grid, lat_grid)


def _colored(rgb: np.ndarray) -> np.ndarray:
    spread = rgb.max(axis=2).astype(int) - rgb.min(axis=2).astype(int)
    return spread > 28


def _slope(stack: np.ndarray, when: np.ndarray, valid: np.ndarray, minimum: int) -> np.ndarray:
    slopes = np.full(stack.shape[1:], np.nan, dtype=np.float32)
    height, width = slopes.shape
    for y in range(height):
        for x in range(width):
            keep = valid[:, y, x]
            if int(keep.sum()) < minimum:
                continue
            slopes[y, x] = np.polyfit(when[keep], stack[keep, y, x], 1)[0]
    return slopes


def _trend_image(slope: np.ndarray, limit: float) -> Image.Image:
    paint = np.nan_to_num(slope, nan=0.0) / limit
    paint = np.clip(paint, -1.0, 1.0)
    image = np.zeros(slope.shape + (4,), dtype=np.uint8)
    negative = paint < 0
    positive = ~negative
    # Tan at zero, red where the series falls, green where it rises.
    image[negative, 0] = (196 + paint[negative] * (196 - 176)).astype(np.uint8)
    image[negative, 1] = (176 + paint[negative] * (176 - 48)).astype(np.uint8)
    image[negative, 2] = (130 + paint[negative] * (130 - 36)).astype(np.uint8)
    image[positive, 0] = (196 + paint[positive] * (46 - 196)).astype(np.uint8)
    image[positive, 1] = (176 + paint[positive] * (130 - 176)).astype(np.uint8)
    image[positive, 2] = (130 + paint[positive] * (58 - 130)).astype(np.uint8)
    image[..., 3] = np.where(np.isfinite(slope), 220, 0)
    return Image.fromarray(image, "RGBA")


def _save(image: Image.Image, name: str) -> None:
    scale = max(1, math.ceil(900 / max(image.width, image.height)))
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(OUT / name)


def _power(path: str, lon: float, lat: float, start, end) -> dict:
    query = urlencode(
        {
            "parameters": "PRECTOTCORR",
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": start,
            "end": end,
            "format": "JSON",
        }
    )
    url = f"https://power.larc.nasa.gov/api/temporal/{path}?" + query
    with urlopen(url, timeout=50) as response:
        payload = json.load(response)
    return payload["properties"]["parameter"]["PRECTOTCORR"]


def rain_report() -> dict:
    monthly = _power("monthly/point", RAIN_POINT[0], RAIN_POINT[1], 2016, 2026)
    septembers = {}
    for year in MODIS_YEARS:
        value = monthly.get(f"{year}09")
        if value is None or value < 0:
            continue
        septembers[str(year)] = round(float(value) * 30.0, 1)
    daily = _power("daily/point", RAIN_POINT[0], RAIN_POINT[1], "20260630", "20261028")
    months = {}
    for key, value in daily.items():
        if value is None or value < 0 or not ("20260630" <= key <= "20261028"):
            continue
        months[key[:6]] = round(months.get(key[:6], 0.0) + float(value), 1)
    return {
        "source": "NASA POWER PRECTOTCORR, mm",
        "september_center": septembers,
        "nisar_months": months,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    polygon = _municipality()

    print("MODIS")
    modis = []
    modis_valid = []
    for year in MODIS_YEARS:
        day = f"{year}-09-01"
        image = _crop(*_mosaic(MODIS_LAYER, day, MODIS_ZOOM, "GoogleMapsCompatible_Level7", False), MODIS_ZOOM)
        rgb = np.asarray(image)
        inside = _inside(rgb.shape[0], rgb.shape[1], MODIS_ZOOM, polygon)
        cloud = rgb.min(axis=2) > 190
        keep = inside & ~cloud
        modis.append(rgb[:, :, 1].astype(np.float32))
        modis_valid.append(keep)
        _save(Image.fromarray(np.dstack([rgb, np.where(keep, 255, 0).astype(np.uint8)]), "RGBA"), f"modis-{year}.png")
    modis_stack = np.stack(modis)
    modis_ok = np.stack(modis_valid)
    modis_slope = _slope(modis_stack, np.array(MODIS_YEARS, dtype=float), modis_ok, 8)
    _save(_trend_image(modis_slope, 2.0), "modis-trend.png")

    print("NISAR")
    nisar = []
    nisar_valid = []
    nisar_means = {}
    elapsed = np.array([(date.fromisoformat(day) - date.fromisoformat(NISAR_DATES[0])).days for day in NISAR_DATES], dtype=float)
    for day in NISAR_DATES:
        image = _crop(*_mosaic(NISAR_LAYER, day, NISAR_ZOOM, "GoogleMapsCompatible_Level13", True), NISAR_ZOOM)
        rgb = np.asarray(image)
        inside = _inside(rgb.shape[0], rgb.shape[1], NISAR_ZOOM, polygon)
        keep = inside & _colored(rgb)
        nisar.append(rgb[:, :, 1].astype(np.float32))
        nisar_valid.append(keep)
        nisar_means[day] = round(float(rgb[:, :, 1][keep].mean()), 1) if keep.any() else None
        alpha = np.where(keep, 255, 0).astype(np.uint8)
        _save(Image.fromarray(np.dstack([rgb, alpha]), "RGBA"), f"nisar-{day}.png")
    nisar_stack = np.stack(nisar)
    nisar_ok = np.stack(nisar_valid)
    nisar_slope = _slope(nisar_stack, elapsed, nisar_ok, 4)
    _save(_trend_image(nisar_slope, 0.4), "nisar-trend.png")

    used = np.isfinite(modis_slope)
    nisar_used = np.isfinite(nisar_slope)
    falling = used & (modis_slope < -0.3)
    nisar_m = 156543.03392 * math.cos(math.radians(RAIN_POINT[1])) / 2**NISAR_ZOOM
    modis_m = 156543.03392 * math.cos(math.radians(RAIN_POINT[1])) / 2**MODIS_ZOOM
    stats = {
        "place": "Jardim do Seridó, RN",
        "west": BBOX[0],
        "south": BBOX[1],
        "east": BBOX[2],
        "north": BBOX[3],
        "modis_years": MODIS_YEARS,
        "nisar_dates": NISAR_DATES,
        "modis_slope_per_year": round(float(np.nanmean(modis_slope)), 2),
        "modis_falling_pct": round(100.0 * float(falling.sum()) / float(used.sum()), 1) if used.any() else None,
        "nisar_means": nisar_means,
        "nisar_slope_per_day": round(float(np.nanmean(nisar_slope)), 3) if nisar_used.any() else None,
        "nisar_pixel_m": round(nisar_m),
        "modis_pixel_m": round(modis_m),
        "rain": rain_report(),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
