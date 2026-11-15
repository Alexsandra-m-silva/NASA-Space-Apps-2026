"""Vegetation decline for five whole semi-arid municipalities.

MODIS September 2016–2026 is the multi-year dry-season series and covers
each municipality. NISAR has no earlier years: only passes of one descending
track, one frame and one polarization (SHSH). Dates that switched to DHDH
are left out. Tiles without a colored preview are dropped, so part of a
large municipality can stay empty.

The map keeps pixels whose slope is negative. The NISAR green channel is
the public preview, not gamma0 in dB, and each GIBS tile is stretched
on its own.
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
from shapely import contains_xy, make_valid
from shapely.geometry import shape
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "municipios"
NISAR_LAYER = "NISAR_L2_Geocoded_Polarimetric_Covariance"
MODIS_LAYER = "MODIS_Terra_L3_NDVI_Monthly"
NISAR_ZOOM = 9
MODIS_ZOOM = 7
MODIS_YEARS = list(range(2016, 2027))

# Same descending track, frame and SHSH polarization inside each group.
TRACK_168 = ["2026-06-25", "2026-07-19", "2026-08-12", "2026-09-05", "2026-09-29", "2026-10-23"]
TRACK_067 = ["2026-06-30", "2026-07-24", "2026-08-17", "2026-09-10", "2026-10-04", "2026-10-28"]
TRACK_096 = ["2026-07-02", "2026-07-26", "2026-08-19", "2026-09-12", "2026-10-06", "2026-10-30"]

PLACES = [
    {
        "slug": "floresta",
        "name": "Floresta",
        "uf": "PE",
        "ibge_uf": "26",
        "nisar_dates": TRACK_168,
        "orbit": "descendente 168, quadro 093, SHSH",
    },
    {
        "slug": "currais-novos",
        "name": "Currais Novos",
        "uf": "RN",
        "ibge_uf": "24",
        "nisar_dates": TRACK_067,
        "orbit": "descendente 067, quadro 092, SHSH",
    },
    {
        "slug": "parelhas",
        "name": "Parelhas",
        "uf": "RN",
        "ibge_uf": "24",
        "nisar_dates": TRACK_067,
        "orbit": "descendente 067, quadro 092, SHSH",
    },
    {
        "slug": "petrolina",
        "name": "Petrolina",
        "uf": "PE",
        "ibge_uf": "26",
        "nisar_dates": TRACK_096,
        "orbit": "descendente 096, quadro 093, SHSH",
    },
    {
        "slug": "casa-nova",
        "name": "Casa Nova",
        "uf": "BA",
        "ibge_uf": "29",
        "nisar_dates": TRACK_096,
        "orbit": "descendente 096, quadro 093, SHSH",
    },
]

_TILES: dict[str, Image.Image] = {}
_MUNICIPALITIES: dict[str, dict] = {}


def _tile_frac(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2**z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def _fetch(url: str) -> Image.Image:
    cached = _TILES.get(url)
    if cached is not None:
        return cached
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
        image = Image.open(BytesIO(data)).convert("RGB")
        _TILES[url] = image
        return image
    raise RuntimeError(f"{url} {last}")


def _mosaic(bbox, layer: str, day: str, z: int, matrix: str, drop_grey: bool) -> tuple[Image.Image, tuple[int, int]]:
    x0, y_north = _tile_frac(bbox[0], bbox[3], z)
    x1, y_south = _tile_frac(bbox[2], bbox[1], z)
    xs = range(math.floor(x0), math.floor(x1) + 1)
    ys = range(math.floor(y_north), math.floor(y_south) + 1)
    canvas = Image.new("RGB", (len(xs) * 256, len(ys) * 256))
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            url = (
                "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
                f"{layer}/default/{day}/{matrix}/{z}/{y}/{x}.png"
            )
            tile = _fetch(url).copy()
            average = np.asarray(tile).reshape(-1, 3).mean(axis=0)
            grey = abs(average[0] - average[1]) < 12 and abs(average[1] - average[2]) < 12
            if drop_grey and grey:
                tile = Image.new("RGB", tile.size)
                print(f"  {day} {z}/{y}/{x} grey, dropped")
            else:
                print(f"  {day} {z}/{y}/{x}")
            canvas.paste(tile, (ix * 256, iy * 256))
    return canvas, (math.floor(x0), math.floor(y_north))


def _crop(canvas: Image.Image, origin: tuple[int, int], z: int, bbox) -> Image.Image:
    x0, y_north = _tile_frac(bbox[0], bbox[3], z)
    x1, y_south = _tile_frac(bbox[2], bbox[1], z)
    left = int(round((x0 - origin[0]) * 256))
    right = int(round((x1 - origin[0]) * 256))
    top = int(round((y_north - origin[1]) * 256))
    bottom = int(round((y_south - origin[1]) * 256))
    return canvas.crop((left, top, max(left + 1, right), max(top + 1, bottom)))


def _municipality(place: dict):
    key = place["ibge_uf"]
    if key not in _MUNICIPALITIES:
        url = f"https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-{key}-mun.json"
        with urlopen(url, timeout=60) as response:
            _MUNICIPALITIES[key] = json.load(response)
    feature = next(item for item in _MUNICIPALITIES[key]["features"] if item["properties"]["name"] == place["name"])
    folder = OUT / place["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "municipality.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}))
    return orient(make_valid(shape(feature["geometry"])), sign=1.0)


def _inside(bbox, height: int, width: int, zoom: int, polygon) -> np.ndarray:
    x_west, y_north = _tile_frac(bbox[0], bbox[3], zoom)
    x_east, y_south = _tile_frac(bbox[2], bbox[1], zoom)
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
    weights = when.astype(np.float64)
    mask = valid.astype(np.float64)
    values = np.where(valid, stack, 0.0).astype(np.float64)
    count = mask.sum(axis=0)
    sum_x = (mask * weights[:, None, None]).sum(axis=0)
    sum_x2 = (mask * (weights * weights)[:, None, None]).sum(axis=0)
    sum_y = values.sum(axis=0)
    sum_xy = (values * weights[:, None, None]).sum(axis=0)
    denominator = count * sum_x2 - sum_x * sum_x
    numerator = count * sum_xy - sum_x * sum_y
    slopes = np.full(count.shape, np.nan, dtype=np.float32)
    ok = (count >= minimum) & (np.abs(denominator) > 1e-9)
    slopes[ok] = (numerator[ok] / denominator[ok]).astype(np.float32)
    return slopes


def _trend_image(slope: np.ndarray, limit: float) -> Image.Image:
    paint = np.nan_to_num(slope, nan=0.0) / limit
    paint = np.clip(paint, -1.0, 1.0)
    image = np.zeros(slope.shape + (4,), dtype=np.uint8)
    negative = paint < 0
    positive = ~negative
    image[negative, 0] = (196 + paint[negative] * (196 - 176)).astype(np.uint8)
    image[negative, 1] = (176 + paint[negative] * (176 - 48)).astype(np.uint8)
    image[negative, 2] = (130 + paint[negative] * (130 - 36)).astype(np.uint8)
    image[positive, 0] = (196 + paint[positive] * (46 - 196)).astype(np.uint8)
    image[positive, 1] = (176 + paint[positive] * (130 - 176)).astype(np.uint8)
    image[positive, 2] = (130 + paint[positive] * (58 - 130)).astype(np.uint8)
    image[..., 3] = np.where(np.isfinite(slope) & (slope < 0), 220, 0)
    return Image.fromarray(image, "RGBA")


def _save(folder: Path, image: Image.Image, name: str) -> None:
    scale = max(1, math.ceil(900 / max(image.width, image.height)))
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(folder / name)


def _power_parameters(path: str, parameters: str, lon: float, lat: float, start, end) -> dict:
    query = urlencode(
        {
            "parameters": parameters,
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
    return payload["properties"]["parameter"]


def _line_slope(values_x: list[float], values_y: list[float]) -> float:
    return round(float(np.polyfit(values_x, values_y, 1)[0]), 3)


def rain_report(place: dict, lon: float, lat: float) -> dict:
    import calendar
    climate = _power_parameters("monthly/point", "PRECTOTCORR,T2M", lon, lat, 2001, 2026)
    rain = climate["PRECTOTCORR"]
    temperature = climate["T2M"]
    annual = []
    september = []
    for year in range(2001, 2027):
        complete = True
        total = 0.0
        temperature_sum = 0.0
        september_rain = None
        september_temperature = None
        for month in range(1, 13):
            key = f"{year}{month:02d}"
            rain_value = rain.get(key)
            temperature_value = temperature.get(key)
            if rain_value is None or temperature_value is None or rain_value < 0 or temperature_value < -50:
                complete = False
                continue
            total += float(rain_value) * calendar.monthrange(year, month)[1]
            temperature_sum += float(temperature_value)
            if month == 9:
                september_rain = round(float(rain_value) * 30.0, 1)
                september_temperature = round(float(temperature_value), 2)
        if september_rain is not None:
            september.append({"year": year, "precip_mm": september_rain, "temp_c": september_temperature})
        if complete:
            annual.append({"year": year, "precip_mm": round(total, 1), "temp_c": round(temperature_sum / 12.0, 2)})
    september_window = [item for item in september if item["year"] >= 2016]
    annual_window = [item for item in annual if 2016 <= item["year"] <= 2025]

    def series_slope(rows: list[dict], key: str) -> float | None:
        if len(rows) < 3:
            return None
        return _line_slope([row["year"] for row in rows], [row[key] for row in rows])

    start = place["nisar_dates"][0].replace("-", "")
    end = place["nisar_dates"][-1].replace("-", "")
    daily = _power_parameters("daily/point", "PRECTOTCORR", lon, lat, start, end)["PRECTOTCORR"]
    months = {}
    for key, value in daily.items():
        if value is None or value < 0 or not (start <= key <= end):
            continue
        months[key[:6]] = round(months.get(key[:6], 0.0) + float(value), 1)
    return {
        "source": "NASA POWER PRECTOTCORR e T2M",
        "annual": annual,
        "september": september,
        "nisar_months": months,
        "slopes": {
            "annual_precip_mm_per_year": series_slope(annual, "precip_mm"),
            "annual_temp_c_per_year": series_slope(annual, "temp_c"),
            "september_precip_mm_per_year": series_slope(september, "precip_mm"),
            "september_temp_c_per_year": series_slope(september, "temp_c"),
            "modis_years_annual_precip_mm_per_year": series_slope(annual_window, "precip_mm"),
            "modis_years_september_precip_mm_per_year": series_slope(september_window, "precip_mm"),
            "modis_years_september_temp_c_per_year": series_slope(september_window, "temp_c"),
        },
    }


def build(place: dict) -> dict:
    folder = OUT / place["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    polygon = _municipality(place)
    west, south, east, north = polygon.bounds
    bbox = (west, south, east, north)
    point = polygon.representative_point()
    dates = place["nisar_dates"]
    print("\n==", place["name"], f"{east - west:.2f}° x {north - south:.2f}°", flush=True)

    print("MODIS")
    modis = []
    modis_valid = []
    modis_frames = []
    for year in MODIS_YEARS:
        day = f"{year}-09-01"
        image = _crop(*_mosaic(bbox, MODIS_LAYER, day, MODIS_ZOOM, "GoogleMapsCompatible_Level7", False), MODIS_ZOOM, bbox)
        rgb = np.asarray(image)
        inside = _inside(bbox, rgb.shape[0], rgb.shape[1], MODIS_ZOOM, polygon)
        cloud = rgb.min(axis=2) > 190
        modis.append(rgb[:, :, 1].astype(np.float32))
        modis_valid.append(inside & ~cloud)
        modis_frames.append(rgb)
    modis_slope = _slope(np.stack(modis), np.array(MODIS_YEARS, dtype=float), np.stack(modis_valid), 8)
    modis_decline = np.isfinite(modis_slope) & (modis_slope < 0)
    for year, rgb in zip(MODIS_YEARS, modis_frames):
        alpha = np.where(modis_decline, 255, 0).astype(np.uint8)
        _save(folder, Image.fromarray(np.dstack([rgb, alpha]), "RGBA"), f"modis-{year}.png")
    _save(folder, _trend_image(modis_slope, 2.0), "modis-trend.png")

    print("NISAR")
    nisar = []
    nisar_valid = []
    nisar_frames = []
    elapsed = np.array([(date.fromisoformat(day) - date.fromisoformat(dates[0])).days for day in dates], dtype=float)
    for day in dates:
        image = _crop(*_mosaic(bbox, NISAR_LAYER, day, NISAR_ZOOM, "GoogleMapsCompatible_Level13", True), NISAR_ZOOM, bbox)
        rgb = np.asarray(image)
        inside = _inside(bbox, rgb.shape[0], rgb.shape[1], NISAR_ZOOM, polygon)
        nisar.append(rgb[:, :, 1].astype(np.float32))
        nisar_valid.append(inside & _colored(rgb))
        nisar_frames.append(rgb)
    nisar_slope = _slope(np.stack(nisar), elapsed, np.stack(nisar_valid), 4)
    nisar_decline = np.isfinite(nisar_slope) & (nisar_slope < 0)
    nisar_means = {}
    for day, rgb in zip(dates, nisar_frames):
        alpha = np.where(nisar_decline, 255, 0).astype(np.uint8)
        _save(folder, Image.fromarray(np.dstack([rgb, alpha]), "RGBA"), f"nisar-{day}.png")
        nisar_means[day] = round(float(rgb[:, :, 1][nisar_decline].mean()), 1) if nisar_decline.any() else None
    _save(folder, _trend_image(nisar_slope, 0.4), "nisar-trend.png")

    used = np.isfinite(modis_slope)
    nisar_used = np.isfinite(nisar_slope)
    nisar_inside = _inside(bbox, nisar_slope.shape[0], nisar_slope.shape[1], NISAR_ZOOM, polygon)
    center_lat = (south + north) / 2
    cover = round(100.0 * float(nisar_used.sum()) / float(nisar_inside.sum()), 1) if nisar_inside.any() else None
    falling = round(100.0 * float(nisar_decline.sum()) / float(nisar_used.sum()), 1) if nisar_used.any() else None
    note = (
        "Município inteiro. O MODIS cobre o território. "
        f"O NISAR dessa órbita tem prévia em {cover}% dos pixels; o restante fica transparente."
    )
    stats = {
        "slug": place["slug"],
        "place": f"{place['name']}, {place['uf']}",
        "name": place["name"],
        "uf": place["uf"],
        "note": note,
        "orbit": place["orbit"],
        "west": round(west, 5),
        "south": round(south, 5),
        "east": round(east, 5),
        "north": round(north, 5),
        "modis_years": MODIS_YEARS,
        "nisar_dates": dates,
        "modis_slope_per_year": round(float(modis_slope[modis_decline].mean()), 2) if modis_decline.any() else None,
        "modis_falling_pct": round(100.0 * float(modis_decline.sum()) / float(used.sum()), 1) if used.any() else None,
        "nisar_means": nisar_means,
        "nisar_slope_per_day": round(float(nisar_slope[nisar_decline].mean()), 3) if nisar_decline.any() else None,
        "nisar_falling_pct": falling,
        "nisar_cover_pct": cover,
        "nisar_pixel_m": round(156543.03392 * math.cos(math.radians(center_lat)) / 2**NISAR_ZOOM),
        "modis_pixel_m": round(156543.03392 * math.cos(math.radians(center_lat)) / 2**MODIS_ZOOM),
        "rain": rain_report(place, float(point.x), float(point.y)),
    }
    (folder / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps({k: stats[k] for k in ("place", "modis_falling_pct", "modis_slope_per_year", "nisar_cover_pct", "nisar_falling_pct", "nisar_slope_per_day")}, indent=2), flush=True)
    return stats


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    built = [build(place) for place in PLACES]
    index = {
        "places": [
            {
                "slug": item["slug"],
                "place": item["place"],
                "west": item["west"],
                "south": item["south"],
                "east": item["east"],
                "north": item["north"],
                "modis_falling_pct": item["modis_falling_pct"],
                "nisar_falling_pct": item["nisar_falling_pct"],
            }
            for item in built
        ]
    }
    (OUT / "index.json").write_text(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
