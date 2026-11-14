"""Build a before/after flood scene from public NISAR GIBS tiles.

Validation site, one reach of the Uruguay River at Uruguaiana.
Same descending track 010, frame 103, one 12-day cycle:
30 Sep 2026 (before the peak) and 12 Oct 2026 (flood week, displacements).

Open water in the GIBS false-color mosaic is the dark, low-backscatter class.
This is a browse-resolution proxy (~33 m), not a calibrated gamma0 threshold.
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
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "scenes"
STATS = ROOT / "web" / "scenes" / "change_stats.json"

BEFORE = "2026-09-30"
AFTER = "2026-10-12"
# west, south, east, north — one river reach, about 15 km
BBOX = (-57.12, -29.83, -56.97, -29.70)
ZOOM = 12
# Dark class in the public false-color GCOV mosaic.
WATER_LUM = 40
# Require a clear brightness jump so speckle is not counted as change.
LAND_LUM = 75
LAYER = "NISAR_L2_Geocoded_Polarimetric_Covariance"


def _tile_xy(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


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
        return Image.new("RGB", (256, 256), (0, 0, 0))
    if len(data) < 400:
        return Image.new("RGB", (256, 256), (0, 0, 0))
    im = Image.open(BytesIO(data)).convert("RGB")
    arr = np.asarray(im)
    # Tiles outside the swath sometimes come back as grey fill, not empty black.
    if arr.mean() > 8 and (arr[:, :, 1].mean() - arr[:, :, 2].mean()) < 8:
        return Image.new("RGB", (256, 256), (0, 0, 0))
    return im


def mosaic(date: str) -> Image.Image:
    west, south, east, north = BBOX
    x0, y_north = _tile_xy(north, west, ZOOM)
    x1, y_south = _tile_xy(south, east, ZOOM)
    xs = range(min(x0, x1), max(x0, x1) + 1)
    ys = range(min(y_north, y_south), max(y_north, y_south) + 1)
    canvas = Image.new("RGB", (len(xs) * 256, len(ys) * 256))
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            canvas.paste(_fetch(date, ZOOM, x, y), (ix * 256, iy * 256))
            print(f"  {date} {x},{y}")
    return canvas


def main() -> None:
    print("mosaic before")
    before = mosaic(BEFORE)
    print("mosaic after")
    after = mosaic(AFTER)
    lb = np.asarray(before).mean(axis=2)
    la = np.asarray(after).mean(axis=2)
    water_b = (lb < WATER_LUM) & (lb > 8)
    water_a = (la < WATER_LUM) & (la > 8)
    new = water_a & (lb >= LAND_LUM)
    gone = water_b & (la >= LAND_LUM)
    change_arr = np.asarray(after).copy()
    change_arr[new] = (255, 48, 48)
    change_arr[gone] = (48, 210, 255)
    change = Image.fromarray(change_arr)
    water_before = int(water_b.sum())
    water_after = int(water_a.sum())
    new_water = int(new.sum())
    receded = int(gone.sum())
    lat = (BBOX[1] + BBOX[3]) / 2
    m_per_px = 156543.03392 * math.cos(math.radians(lat)) / (2**ZOOM)
    ha = (m_per_px * m_per_px) / 10000.0
    stats = {
        "place": "Uruguay River at Uruguaiana, Rio Grande do Sul, Brazil",
        "event": "Uruguay River flood, October–November 2026",
        "climate_action": (
            "This reach is the check site. 12 Oct is the flood week: Copernicus EMS "
            "reported 289 people displaced in Itaqui and 217 in Uruguaiana. "
            "30 Sep is the same orbit one cycle earlier, before that peak."
        ),
        "product": "NISAR_L2_GCOV_PROVISIONAL_V1",
        "granule_before": "NISAR_L2_PR_GCOV_032_010_D_103_2005_DHDH_A_20260930T215847_20260930T215922_P05023_N_F_J_001",
        "granule_after": "NISAR_L2_PR_GCOV_033_010_D_103_2005_DHDH_A_20261012T215847_20261012T215922_P05023_N_F_J_001",
        "geometry": "Same descending track 010, frame 103, dual-pol HH/HV, 12-day repeat",
        "before": BEFORE,
        "after": AFTER,
        "bbox": list(BBOX),
        "center": [lat, (BBOX[0] + BBOX[2]) / 2],
        "zoom": 13,
        "method": (
            "Open-water proxy on the public GIBS false-color mosaic of provisional "
            "GCOV: mean RGB below 40, and a jump from land brightness (>=75) so "
            "speckle is not counted. Browse pixels are about 33 m, not the native "
            "10–20 m gamma0 grid."
        ),
        "pixel_m": round(m_per_px, 2),
        "water_before_ha": round(water_before * ha, 1),
        "water_after_ha": round(water_after * ha, 1),
        "new_inundation_ha": round(new_water * ha, 1),
        "receded_ha": round(receded * ha, 1),
        "sources": [
            "https://global-flood.emergency.copernicus.eu/news/264-parana-river-floods-in-paraguay-argentina-and-brazil-october-2026",
            "https://www.defesacivil.rs.gov.br/centro-de-monitoramento-da-defesa-civil-atualiza-o-prognostico-hidrologico-para-os-proximos-dias",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    STATS.parent.mkdir(parents=True, exist_ok=True)
    before.save(OUT / "before.png", optimize=True)
    after.save(OUT / "after.png", optimize=True)
    change.save(OUT / "change.png", optimize=True)
    STATS.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
