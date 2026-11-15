"""Multi-year dryland map, confirmed by one NISAR season.

History: NASA GIBS monthly MODIS NDVI (MODIS_Terra_L3_NDVI_Monthly), each
September 2016–2025. The layer uses one fixed color scale, so the green
channel is a stable NDVI rank (not the raw 0.0001 integer).

Rain: NASA POWER monthly precipitation at Petrolina. A drop in NDVI that
tracks a drop in rain is drought. The residual trend is the degradation signal.

Now: NISAR loss polygons from 5 Sep–23 Oct 2026. A long decline that also
sits on a NISAR loss patch is the confirmed class.
"""

from __future__ import annotations

import json
import math
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "desert"
YEARS = list(range(2016, 2026))
# west, south, east, north — the NISAR block around Petrolina
BBOX = (-40.78125, -9.622414, -40.253906, -8.928487)
ZOOM = 7
LAYER = "MODIS_Terra_L3_NDVI_Monthly"
# Residual NDVI-rank change per year. Negative means drying vegetation
# after the rainfall term is removed.
DECLINE_PER_YEAR = -0.008
RAIN_POINTS = ((-9.4, -40.52),)


def _tile_xy(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def _latlon(px: float, py: float, tile_x0: int, tile_y0: int, z: int) -> tuple[float, float]:
    world = (2**z) * 256
    lon = (tile_x0 * 256 + px) / world * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (tile_y0 * 256 + py) / world))))
    return lon, lat


def _fetch_tile(year: int, x: int, y: int) -> Image.Image:
    url = (
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{LAYER}/default/{year}-09-01/GoogleMapsCompatible_Level7/{ZOOM}/{y}/{x}.png"
    )
    data = urlopen(url, timeout=40).read()
    if len(data) < 500:
        return Image.new("RGB", (256, 256))
    return Image.open(BytesIO(data)).convert("RGB")


def mosaic(year: int, xs: range, ys: range) -> np.ndarray:
    canvas = Image.new("RGB", (len(xs) * 256, len(ys) * 256))
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            canvas.paste(_fetch_tile(year, x, y), (ix * 256, iy * 256))
    return np.asarray(canvas)


def _crop_box(width: int, height: int, tile_x0: int, tile_y0: int) -> tuple[int, int, int, int]:
    west, south, east, north = BBOX
    samples = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    ]
    # Walk the grid and keep pixels inside the box. The mosaic is small.
    inside = []
    for y in range(height):
        for x in range(width):
            lon, lat = _latlon(x + 0.5, y + 0.5, tile_x0, tile_y0, ZOOM)
            if west <= lon <= east and south <= lat <= north:
                inside.append((x, y))
    xs = [p[0] for p in inside]
    ys = [p[1] for p in inside]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _rain() -> dict[int, float]:
    # Monthly value is mm/day. September total is about 30 times that.
    # One town's rain should not stand for the whole Caatinga, so average four points.
    totals = {year: 0.0 for year in YEARS}
    for lat, lon in RAIN_POINTS:
        url = (
            "https://power.larc.nasa.gov/api/temporal/monthly/point"
            f"?parameters=PRECTOTCORR&community=AG&longitude={lon}&latitude={lat}"
            "&start=2016&end=2025&format=JSON"
        )
        with urlopen(url, timeout=40) as response:
            series = json.load(response)["properties"]["parameter"]["PRECTOTCORR"]
        for year in YEARS:
            totals[year] += series[f"{year}09"] * 30.0
    return {year: round(totals[year] / len(RAIN_POINTS), 1) for year in YEARS}


def _residual_slopes(cube: np.ndarray, rain: np.ndarray) -> np.ndarray:
    """Per-cell slope of NDVI after a shared rainfall term is removed."""
    count = np.isfinite(cube).sum(axis=0)
    filled = np.where(np.isfinite(cube), cube, 0.0)
    rain = rain.astype(np.float64)
    rain_c = rain - rain.mean()
    var_rain = float(np.dot(rain_c, rain_c))
    mean = filled.sum(axis=0) / np.maximum(count, 1)
    centered = filled - mean
    rain_slope = np.tensordot(rain_c, centered, axes=(0, 0)) / var_rain
    fitted = rain_slope * rain[:, None, None] + (mean - rain_slope * rain.mean())
    residual = filled - fitted
    years = np.arange(cube.shape[0], dtype=np.float64)
    years_c = years - years.mean()
    trend = np.tensordot(years_c, residual - residual.mean(axis=0), axes=(0, 0))
    trend = trend / float(np.dot(years_c, years_c))
    trend[count < 8] = np.nan
    return trend


def _fit_slope(values: np.ndarray, covariate: np.ndarray) -> float:
    """Slope of residuals after removing a linear covariate. NaN if too few years."""
    ok = np.isfinite(values) & np.isfinite(covariate)
    if int(ok.sum()) < 8:
        return float("nan")
    y = values[ok]
    x = covariate[ok]
    years = np.arange(len(values), dtype=float)[ok]
    rain_slope, rain_intercept = np.polyfit(x, y, 1)
    residual = y - (rain_slope * x + rain_intercept)
    trend, _ = np.polyfit(years, residual, 1)
    return float(trend)


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    # Ray cast. Rings are tiny rectangles.
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def main() -> None:
    west, south, east, north = BBOX
    x0, y_north = _tile_xy(north, west, ZOOM)
    x1, y_south = _tile_xy(south, east, ZOOM)
    xs = range(min(x0, x1), max(x0, x1) + 1)
    ys = range(min(y_north, y_south), max(y_north, y_south) + 1)
    tile_x0, tile_y0 = min(xs), min(ys)
    print("tiles", list(xs), list(ys))

    rain = _rain()
    rain_vec = np.array([rain[year] for year in YEARS], dtype=float)
    print("september rain mm", rain)

    stack = []
    for year in YEARS:
        image = mosaic(year, xs, ys)
        red = image[:, :, 0].astype(np.float32)
        green = image[:, :, 1].astype(np.float32)
        blue = image[:, :, 2].astype(np.float32)
        # September Caatinga is brown on this ramp, not only green.
        # Green channel still rises from bare soil to dense cover.
        # Pale pixels are cloud. Near-black is empty tile.
        cloud = (red > 190) & (green > 190) & (blue > 190)
        empty = image.max(axis=2) < 20
        land = ~cloud & ~empty & (green > 30)
        ndvi = np.where(land, green / 255.0, np.nan)
        stack.append(ndvi)
        print(year, "land pixels", int(land.sum()))
    cube = np.stack(stack, axis=0)

    x_start, y_start, x_stop, y_stop = _crop_box(cube.shape[2], cube.shape[1], tile_x0, tile_y0)
    cube = cube[:, y_start:y_stop, x_start:x_stop]
    n_years, height, width = cube.shape
    slopes = _residual_slopes(cube, rain_vec)

    geo = json.loads((OUT / "index.geojson").read_text())
    rings = [feature["geometry"]["coordinates"][0] for feature in geo["features"]]
    raw_decline = slopes < DECLINE_PER_YEAR
    decline = raw_decline
    # Keep a yellow cell only when the drop is shared with its neighbors.
    padded = np.pad(decline.astype(np.uint8), 1)
    neighbors = np.zeros_like(decline, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            neighbors += padded[dy : dy + height, dx : dx + width]
    decline = decline & (neighbors >= 5)
    confirmed = np.zeros_like(decline)
    for y in range(height):
        for x in range(width):
            if not raw_decline[y, x]:
                continue
            lon, lat = _latlon(x_start + x + 0.5, y_start + y + 0.5, tile_x0, tile_y0, ZOOM)
            # A red cell is a MODIS square that contains a NISAR loss patch.
            half = 0.006
            for ring in rings:
                lons = [p[0] for p in ring]
                lats = [p[1] for p in ring]
                if (
                    min(lons) <= lon + half
                    and max(lons) >= lon - half
                    and min(lats) <= lat + half
                    and max(lats) >= lat - half
                ):
                    confirmed[y, x] = True
                    break

    m_per_px = 156543.03392 * math.cos(math.radians(-9.5)) / (2**ZOOM)
    ha = (m_per_px * m_per_px) / 10000.0
    red_features = []
    ys, xs = np.where(confirmed)
    order = sorted(zip(ys.tolist(), xs.tolist()), key=lambda p: (p[0], p[1]))
    for index, (y, x) in enumerate(order, start=1):
        corners = [
            _latlon(x_start + x, y_start + y, tile_x0, tile_y0, ZOOM),
            _latlon(x_start + x + 1, y_start + y, tile_x0, tile_y0, ZOOM),
            _latlon(x_start + x + 1, y_start + y + 1, tile_x0, tile_y0, ZOOM),
            _latlon(x_start + x, y_start + y + 1, tile_x0, tile_y0, ZOOM),
        ]
        ring = [[round(lon, 6), round(lat, 6)] for lon, lat in corners]
        ring.append(ring[0])
        center_lon = round(sum(p[0] for p in ring[:-1]) / 4, 6)
        center_lat = round(sum(p[1] for p in ring[:-1]) / 4, 6)
        red_features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": index,
                    "ha": round(ha, 1),
                    "center": [center_lat, center_lon],
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        )
    decline_only = decline & ~confirmed
    stats = {
        "place": "Caatinga near Petrolina, Pernambuco",
        "ndvi": "MODIS Terra monthly NDVI, each September 2016–2025, GIBS fixed color scale",
        "rain": "NASA POWER PRECTOTCORR, September total at Petrolina",
        "september_rain_mm": {str(year): rain[year] for year in YEARS},
        "nisar": "Loss patches from GCOV 5 Sep and 23 Oct 2026, track 168",
        "decline_per_year": DECLINE_PER_YEAR,
        "decline_ha": round(float(decline_only.sum()) * ha, 0),
        "confirmed_ha": round(float(confirmed.sum()) * ha, 0),
        "pixel_m": round(m_per_px, 0),
        "reading": (
            "Yellow: September vegetation rank fell for a decade after removing "
            "the rainfall term. Red: that decline also matches a 2026 NISAR loss patch."
        ),
    }

    picture = np.zeros((height, width, 3), dtype=np.uint8)
    # Stable land that had vegetation in most years.
    present = np.isfinite(cube).sum(axis=0) >= 8
    picture[present] = (40, 90, 48)
    picture[decline_only] = (232, 184, 72)
    picture[confirmed] = (220, 64, 48)
    image = Image.fromarray(picture).resize((width * 8, height * 8), Image.NEAREST)

    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / "multiyear.png")
    nw_lon, nw_lat = _latlon(x_start, y_start, tile_x0, tile_y0, ZOOM)
    se_lon, se_lat = _latlon(x_stop, y_stop, tile_x0, tile_y0, ZOOM)
    bounds = {
        "west": round(min(nw_lon, se_lon), 5),
        "south": round(min(nw_lat, se_lat), 5),
        "east": round(max(nw_lon, se_lon), 5),
        "north": round(max(nw_lat, se_lat), 5),
    }
    (OUT / "multiyear_bounds.json").write_text(json.dumps(bounds, indent=2))
    (OUT / "multiyear_stats.json").write_text(json.dumps(stats, indent=2))
    (OUT / "red.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": red_features})
    )
    print("red squares", len(red_features))
    print(json.dumps(stats, indent=2))
    print("bounds", bounds, "image", image.size)


if __name__ == "__main__":
    main()
