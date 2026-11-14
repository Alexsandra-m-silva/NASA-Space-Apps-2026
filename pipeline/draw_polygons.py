"""Draw numbered polygons for a human check of one flood reach.

Box is the bank and side channel of the Uruguay River at Uruguaiana where
30 Sep 2026 land became dark water on 12 Oct 2026. Same NISAR orbit.
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
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "scenes"

BEFORE = "2026-09-30"
AFTER = "2026-10-12"
# west, south, east, north — the bank that filled, not the whole swath
BBOX = (-57.079, -29.763, -57.015, -29.718)
ZOOM = 13
WATER_LUM = 40
LAND_LUM = 75
MIN_HA = 8.0
LAYER = "NISAR_L2_Geocoded_Polarimetric_Covariance"


def _tile_xy(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def _latlon(px: float, py: float, tile_x0: int, tile_y0: int, z: int) -> tuple[float, float]:
    n = 2**z
    world = n * 256
    gx = tile_x0 * 256 + px
    gy = tile_y0 * 256 + py
    lon = gx / world * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * gy / world))))
    return lon, lat


def _fetch(date: str, z: int, x: int, y: int) -> Image.Image:
    url = (
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{LAYER}/default/{date}/GoogleMapsCompatible_Level13/{z}/{y}/{x}.png"
    )
    last = None
    for attempt in range(4):
        try:
            data = urlopen(url, timeout=40).read()
            break
        except (HTTPError, URLError, TimeoutError) as exc:
            last = exc
            time.sleep(1.2 * (attempt + 1))
    else:
        print(f"  skip {x},{y}: {last}")
        return Image.new("RGB", (256, 256))
    if len(data) < 400:
        return Image.new("RGB", (256, 256))
    im = Image.open(BytesIO(data)).convert("RGB")
    arr = np.asarray(im)
    if arr.mean() > 8 and (arr[:, :, 1].mean() - arr[:, :, 2].mean()) < 8:
        return Image.new("RGB", (256, 256))
    return im


def mosaic(date: str, xs: range, ys: range) -> Image.Image:
    canvas = Image.new("RGB", (len(xs) * 256, len(ys) * 256))
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            canvas.paste(_fetch(date, ZOOM, x, y), (ix * 256, iy * 256))
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


def _trace(cells: np.ndarray, h: int, w: int) -> list[tuple[int, int]]:
    block = np.zeros((h, w), dtype=bool)
    block[cells[:, 0], cells[:, 1]] = True
    ys, xs = np.where(block)
    sy, sx = int(ys[0]), int(xs[0])
    nbrs = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))
    contour = [(sx, sy)]
    py, px = sy, sx - 1
    cy, cx = sy, sx
    for _ in range(len(cells) * 8):
        try:
            enter = nbrs.index((py - cy, px - cx))
        except ValueError:
            enter = 0
        found = False
        for k in range(1, 9):
            dy, dx = nbrs[(enter + k) % 8]
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and block[ny, nx]:
                py, px = cy, cx
                cy, cx = ny, nx
                contour.append((cx, cy))
                found = True
                break
        if not found or ((cy, cx) == (sy, sx) and len(contour) > 8):
            break
    return contour


def _simplify(ring: list[tuple[int, int]], step: int = 3) -> list[tuple[int, int]]:
    if len(ring) <= 8:
        return ring
    simple = ring[::step]
    if simple[0] != simple[-1]:
        simple.append(simple[0])
    return simple


def _draw(base: Image.Image, polygons: list[dict]) -> Image.Image:
    im = base.convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    paint = overlay.load()
    for poly in polygons:
        for y, x in poly["cells"]:
            if 0 <= x < im.width and 0 <= y < im.height:
                paint[int(x), int(y)] = (255, 40, 40, 140)
        for y, x in poly["edge"]:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = int(x) + dx, int(y) + dy
                    if 0 <= xx < im.width and 0 <= yy < im.height:
                        paint[xx, yy] = (255, 230, 40, 255)
    pen = ImageDraw.Draw(overlay)
    for poly in polygons:
        ys = poly["cells"][:, 0]
        xs = poly["cells"][:, 1]
        label = (int(xs.mean()), int(ys.mean()))
        pen.ellipse((label[0] - 14, label[1] - 14, label[0] + 14, label[1] + 14), fill=(0, 0, 0, 240))
        text = str(poly["id"])
        pen.text((label[0] - 4 * len(text), label[1] - 6), text, fill=(255, 230, 40, 255))
    return Image.alpha_composite(im, overlay).convert("RGB")


def main() -> None:
    west, south, east, north = BBOX
    x0, y_north = _tile_xy(north, west, ZOOM)
    x1, y_south = _tile_xy(south, east, ZOOM)
    xs = range(min(x0, x1), max(x0, x1) + 1)
    ys = range(min(y_north, y_south), max(y_north, y_south) + 1)
    print("tiles", list(xs), list(ys))
    before = mosaic(BEFORE, xs, ys)
    after = mosaic(AFTER, xs, ys)
    lb = np.asarray(before).mean(axis=2)
    la = np.asarray(after).mean(axis=2)
    new = (la < WATER_LUM) & (la > 8) & (lb >= LAND_LUM)
    lat_mid = (south + north) / 2
    m_per_px = 156543.03392 * math.cos(math.radians(lat_mid)) / (2**ZOOM)
    ha_px = (m_per_px * m_per_px) / 10000.0
    tile_x0, tile_y0 = min(xs), min(ys)
    h, w = new.shape
    polygons = []
    for cells in _components(new):
        area_ha = len(cells) * ha_px
        if area_ha < MIN_HA:
            continue
        ring = _simplify(_trace(cells, h, w), step=4)
        if len(ring) < 4:
            continue
        edge = []
        block = np.zeros((h, w), dtype=bool)
        block[cells[:, 0], cells[:, 1]] = True
        for y, x in cells:
            if (
                y == 0
                or x == 0
                or y == h - 1
                or x == w - 1
                or not block[y - 1, x]
                or not block[y + 1, x]
                or not block[y, x - 1]
                or not block[y, x + 1]
            ):
                edge.append((int(x), int(y)))
        coords = []
        for px, py in ring:
            lon, lat = _latlon(px + 0.5, py + 0.5, tile_x0, tile_y0, ZOOM)
            coords.append([round(lon, 6), round(lat, 6)])
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        polygons.append(
            {
                "id": 0,
                "pixels": ring,
                "cells": cells,
                "edge": edge,
                "ha": round(area_ha, 1),
                "coordinates": coords,
            }
        )
    polygons.sort(key=lambda p: p["ha"], reverse=True)
    for i, poly in enumerate(polygons, start=1):
        poly["id"] = i

    all_cells = np.concatenate([p["cells"] for p in polygons])
    pad = 36
    y0 = max(0, int(all_cells[:, 0].min()) - pad)
    y1 = min(before.height, int(all_cells[:, 0].max()) + pad)
    x0 = max(0, int(all_cells[:, 1].min()) - pad)
    x1 = min(before.width, int(all_cells[:, 1].max()) + pad)
    for poly in polygons:
        poly["cells"] = poly["cells"] - np.array([y0, x0])
        poly["edge"] = [(x - x0, y - y0) for x, y in poly["edge"]]
    def _drop_grey(im: Image.Image) -> Image.Image:
        arr = np.asarray(im).copy()
        r = arr[:, :, 0].astype(int)
        g = arr[:, :, 1].astype(int)
        b = arr[:, :, 2].astype(int)
        grey = (np.abs(g - b) < 15) & (np.abs(r - g) < 15) & (arr.mean(axis=2) > 25)
        arr[grey] = 0
        return Image.fromarray(arr)

    before = _drop_grey(before.crop((x0, y0, x1, y1)))
    after = _drop_grey(after.crop((x0, y0, x1, y1)))
    outlined_before = _draw(before, polygons)
    outlined_after = _draw(after, polygons)
    pair = Image.new("RGB", (outlined_before.width * 2 + 12, outlined_before.height), (8, 12, 20))
    pair.paste(outlined_before, (0, 0))
    pair.paste(outlined_after, (outlined_before.width + 12, 0))
    tag = ImageDraw.Draw(pair)
    tag.rectangle((0, 0, 210, 28), fill=(0, 0, 0))
    tag.rectangle((outlined_before.width + 12, 0, outlined_before.width + 222, 28), fill=(0, 0, 0))
    tag.text((8, 8), "30 Sep  before", fill=(255, 230, 40))
    tag.text((outlined_before.width + 20, 8), "12 Oct  flood", fill=(255, 230, 40))

    nw_lon, nw_lat = _latlon(x0, y0, tile_x0, tile_y0, ZOOM)
    se_lon, se_lat = _latlon(x1, y1, tile_x0, tile_y0, ZOOM)
    bounds = {
        "west": round(min(nw_lon, se_lon), 6),
        "south": round(min(nw_lat, se_lat), 6),
        "east": round(max(nw_lon, se_lon), 6),
        "north": round(max(nw_lat, se_lat), 6),
    }
    features = []
    for poly in polygons:
        features.append(
            {
                "type": "Feature",
                "properties": {"id": poly["id"], "ha": poly["ha"], "class": "new open water"},
                "geometry": {"type": "Polygon", "coordinates": [poly["coordinates"]]},
            }
        )
    geojson = {"type": "FeatureCollection", "features": features}
    stats = {
        "place": "Uruguay River bank, Uruguaiana — human check box",
        "before": BEFORE,
        "after": AFTER,
        "bbox": [bounds["west"], bounds["south"], bounds["east"], bounds["north"]],
        "center": [
            round((bounds["south"] + bounds["north"]) / 2, 5),
            round((bounds["west"] + bounds["east"]) / 2, 5),
        ],
        "zoom": 14,
        "polygons": len(polygons),
        "new_inundation_ha": round(sum(p["ha"] for p in polygons), 1),
        "polygon_ha": [{"id": p["id"], "ha": p["ha"]} for p in polygons],
        "check": (
            "Same yellow outline on both dates. On 30 Sep the number should sit on "
            "bright land. On 12 Oct it should sit on dark water. Reject a number that fails either test."
        ),
        "geometry": "Same descending track 010, frame 103, 12-day repeat",
        "pixel_m": round(m_per_px, 2),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    outlined_before.save(OUT / "before.png", optimize=True)
    outlined_after.save(OUT / "after.png", optimize=True)
    pair.save(OUT / "change.png", optimize=True)
    (OUT / "change_polygons.geojson").write_text(json.dumps(geojson))
    (OUT / "change_stats.json").write_text(json.dumps(stats, indent=2))
    (OUT / "bounds.json").write_text(json.dumps(bounds, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
