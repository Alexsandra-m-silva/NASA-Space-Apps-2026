"""Early-warning score for dryland vegetation loss from NISAR GCOV.

Site: Caatinga around Petrolina, Pernambuco.
Same descending track 168, frame 093:
  5 Sep 2026 (provisional GCOV) and 23 Oct 2026 (validated GCOV).

The public false-color mosaic puts cross-pol (HV) in the green channel.
HV is higher where vegetation has structure. A drop in green, on pixels that
were vegetated in September, is a short-term vegetation-structure loss score.

This is an input to a desertification index. One dry-season cycle is not
desertification, which is a multi-year process.
"""

from __future__ import annotations

import json
import math
import time
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "desert"

BEFORE = "2026-09-05"
AFTER = "2026-10-23"
ZOOM = 11
# Tile with real false-color GCOV on both 5 Sep and 23 Oct.
TILES_X = range(793, 794)
TILES_Y = range(1078, 1079)
LAYER = "NISAR_L2_Geocoded_Polarimetric_Covariance"
# Green-channel drop, in browse units, that maps to a score of 1.
LOSS_SCALE = 40
MIN_GREEN = 80
MIN_HA = 2.0
SCORE_MIN = 0.4


def _latlon(px: float, py: float, tile_x0: int, tile_y0: int, z: int) -> tuple[float, float]:
    world = (2**z) * 256
    lon = (tile_x0 * 256 + px) / world * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (tile_y0 * 256 + py) / world))))
    return lon, lat


def _fetch(date: str, x: int, y: int) -> Image.Image:
    url = (
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{LAYER}/default/{date}/GoogleMapsCompatible_Level13/{ZOOM}/{y}/{x}.png"
    )
    last = "no color"
    for attempt in range(6):
        try:
            data = urlopen(url, timeout=40).read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last = exc
            time.sleep(0.8 * (attempt + 1))
            continue
        if len(data) < 8000:
            last = f"short {len(data)}"
            time.sleep(0.6)
            continue
        im = Image.open(BytesIO(data)).convert("RGB")
        arr = np.asarray(im)
        color = np.abs(arr[:, :, 1].astype(int) - arr[:, :, 0].astype(int)).mean()
        if color > 8 and arr.mean() > 15:
            return im
        last = f"not sar color={color:.1f} bytes={len(data)}"
        time.sleep(0.6)
    print(f"  skip {date} {x},{y}: {last}")
    return Image.new("RGB", (256, 256))


def mosaic(date: str) -> Image.Image:
    canvas = Image.new("RGB", (len(TILES_X) * 256, len(TILES_Y) * 256))
    for iy, y in enumerate(TILES_Y):
        for ix, x in enumerate(TILES_X):
            canvas.paste(_fetch(date, x, y), (ix * 256, iy * 256))
            print(f"  {date} {x},{y}")
    return canvas


def _components(mask: np.ndarray) -> list[np.ndarray]:
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    found = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        stack = [(y0, x0)]
        seen[y0, x0] = True
        cells = []
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        found.append(np.array(cells, dtype=int))
    return found


def main() -> None:
    print("mosaic before")
    before = mosaic(BEFORE)
    print("mosaic after")
    after = mosaic(AFTER)
    b = np.asarray(before)
    a = np.asarray(after)
    gb = b[:, :, 1].astype(np.float32)
    ga = a[:, :, 1].astype(np.float32)
    color_b = np.abs(b[:, :, 1].astype(int) - b[:, :, 0].astype(int)) > 8
    color_a = np.abs(a[:, :, 1].astype(int) - a[:, :, 0].astype(int)) > 8
    valid = (b.mean(axis=2) > 12) & (a.mean(axis=2) > 12) & color_b & color_a
    # Grey fill tiles are not SAR.
    grey_b = (np.abs(b[:, :, 1].astype(int) - b[:, :, 2].astype(int)) < 12) & (b.mean(axis=2) > 25)
    grey_a = (np.abs(a[:, :, 1].astype(int) - a[:, :, 2].astype(int)) < 12) & (a.mean(axis=2) > 25)
    valid &= ~grey_b & ~grey_a
    loss = np.clip(gb - ga, 0, None)
    score = np.clip(loss / LOSS_SCALE, 0, 1)
    score[~valid] = 0
    risk = valid & (gb >= MIN_GREEN) & (score >= SCORE_MIN)
    # Drop single-pixel speckle. Keep a pixel only when most of its neighborhood also dropped.
    padded = np.pad(risk, 1)
    h, w = risk.shape
    neighbors = np.zeros_like(risk, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            neighbors += padded[dy : dy + h, dx : dx + w]
    risk = risk & (neighbors >= 6)

    lat = -9.4
    m_per_px = 156543.03392 * math.cos(math.radians(lat)) / (2**ZOOM)
    ha_px = (m_per_px * m_per_px) / 10000.0
    tile_x0, tile_y0 = min(TILES_X), min(TILES_Y)

    heat = after.convert("RGBA")
    paint = heat.load()
    risk_ys, risk_xs = np.where(risk)
    for y, x in zip(risk_ys.tolist(), risk_xs.tolist()):
        paint[x, y] = (255, 170, 40, 255)
    heat = heat.convert("RGB")

    features = []
    areas = []
    for cells in _components(risk):
        area = round(len(cells) * ha_px, 1)
        if area < MIN_HA:
            continue
        ys, xs = cells[:, 0], cells[:, 1]
        ring = [
            _latlon(float(xs.min()), float(ys.min()), tile_x0, tile_y0, ZOOM),
            _latlon(float(xs.max()), float(ys.min()), tile_x0, tile_y0, ZOOM),
            _latlon(float(xs.max()), float(ys.max()), tile_x0, tile_y0, ZOOM),
            _latlon(float(xs.min()), float(ys.max()), tile_x0, tile_y0, ZOOM),
            _latlon(float(xs.min()), float(ys.min()), tile_x0, tile_y0, ZOOM),
        ]
        mean_score = round(float(score[ys, xs].mean()), 2)
        areas.append({"ha": area, "score": mean_score})
        features.append(
            {
                "type": "Feature",
                "properties": {"ha": area, "score": mean_score},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[round(lon, 6), round(lat_, 6)] for lon, lat_ in ring]],
                },
            }
        )
    areas.sort(key=lambda item: item["ha"], reverse=True)

    h, w = score.shape
    nw_lon, nw_lat = _latlon(0, 0, tile_x0, tile_y0, ZOOM)
    se_lon, se_lat = _latlon(w, h, tile_x0, tile_y0, ZOOM)
    bounds = {
        "west": round(min(nw_lon, se_lon), 6),
        "south": round(min(nw_lat, se_lat), 6),
        "east": round(max(nw_lon, se_lon), 6),
        "north": round(max(nw_lat, se_lat), 6),
    }
    scored_px = int((score > 0).sum())
    stats = {
        "place": "Caatinga near Petrolina, Pernambuco, Brazil",
        "product": "Vegetation-structure loss score from NISAR GCOV",
        "not": "This is not a multi-year desertification classification.",
        "before": BEFORE,
        "after": AFTER,
        "geometry": "Same descending track 168, frame 093",
        "granule_hint": "NISAR_L2_GCOV track 168 frame 093, 5 Sep provisional and 23 Oct validated",
        "method": (
            "Score is the drop in the green (cross-pol) browse channel divided by 40, "
            "kept only where September green was at least 80. Polygons are the boxes "
            "around patches of at least 2 ha with score >= 0.40."
        ),
        "mean_score_where_loss": round(float(score[score > 0].mean()) if scored_px else 0, 3),
        "risk_ha": round(sum(item["ha"] for item in areas), 1),
        "patches": areas[:12],
        "bbox": [bounds["west"], bounds["south"], bounds["east"], bounds["north"]],
        "center": [
            round((bounds["south"] + bounds["north"]) / 2, 5),
            round((bounds["west"] + bounds["east"]) / 2, 5),
        ],
        "pixel_m": round(m_per_px, 2),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    before.save(OUT / "before.png", optimize=True)
    after.save(OUT / "after.png", optimize=True)
    heat.save(OUT / "index.png", optimize=True)
    (OUT / "index.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    (OUT / "bounds.json").write_text(json.dumps(bounds, indent=2))
    (OUT / "index_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
