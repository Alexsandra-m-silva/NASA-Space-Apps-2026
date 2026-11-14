"""Before/after vegetation view for one small box near Petrolina.

The box is the same 11 km validation window used for the NISAR products.

MODIS monthly NDVI (GIBS color scale) compares September 2016 with
September 2025. That is the multi-year dry-season vegetation context.

NISAR GCOV browse compares 5 Sep 2026 with 23 Oct 2026, same descending
track 168, frame 093. The green channel of the public false-color image
is the HV preview. It is not gamma0 in dB. Each GIBS tile is stretched on
its own, so a small green drop is a hint, not a measured biomass loss.

Desertification is the multi-year process. The NISAR pair is one 48-day
step inside 2026.
"""

from __future__ import annotations

import json
import math
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "degradation"

# west, south, east, north
BBOX = (-40.55, -9.48, -40.45, -9.40)
NISAR_ZOOM = 11
NISAR_LAYER = "NISAR_L2_Geocoded_Polarimetric_Covariance"
MODIS_ZOOM = 7
MODIS_LAYER = "MODIS_Terra_L3_NDVI_Monthly"
MODIS_BEFORE = "2016-09-01"
MODIS_AFTER = "2025-09-01"
NISAR_BEFORE = "2026-09-05"
NISAR_AFTER = "2026-10-23"


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


def _mosaic(layer: str, day: str, z: int, matrix: str) -> tuple[Image.Image, tuple[int, int]]:
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
            canvas.paste(_fetch(url), (ix * 256, iy * 256))
            print(f"  {layer} {day} {z}/{y}/{x}")
    origin = (math.floor(x0), math.floor(y_north))
    return canvas, origin


def _crop(canvas: Image.Image, origin: tuple[int, int], z: int) -> Image.Image:
    x0, y_north = _tile_frac(BBOX[0], BBOX[3], z)
    x1, y_south = _tile_frac(BBOX[2], BBOX[1], z)
    left = int(round((x0 - origin[0]) * 256))
    right = int(round((x1 - origin[0]) * 256))
    top = int(round((y_north - origin[1]) * 256))
    bottom = int(round((y_south - origin[1]) * 256))
    return canvas.crop((left, top, right, bottom))


def _rain(year: int, month: int) -> float | None:
    query = urlencode(
        {
            "parameters": "PRECTOTCORR",
            "community": "AG",
            "longitude": -40.5,
            "latitude": -9.44,
            "start": year,
            "end": year,
            "format": "JSON",
        }
    )
    url = "https://power.larc.nasa.gov/api/temporal/monthly/point?" + query
    try:
        with urlopen(url, timeout=40) as response:
            payload = json.load(response)
        values = payload["properties"]["parameter"]["PRECTOTCORR"]
        daily = values.get(f"{year}{month:02d}")
    except Exception as exc:  # noqa: BLE001
        print("rain", year, month, exc)
        return None
    if daily is None or daily < 0:
        return None
    return round(float(daily) * 30.0, 1)


def _hv_mask(rgb: np.ndarray) -> np.ndarray:
    return np.abs(rgb[:, :, 1].astype(int) - rgb[:, :, 0].astype(int)) > 8


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("MODIS")
    modis_before_img = _crop(*_mosaic(MODIS_LAYER, MODIS_BEFORE, MODIS_ZOOM, "GoogleMapsCompatible_Level7"), MODIS_ZOOM)
    modis_after_img = _crop(*_mosaic(MODIS_LAYER, MODIS_AFTER, MODIS_ZOOM, "GoogleMapsCompatible_Level7"), MODIS_ZOOM)
    print("NISAR")
    nisar_before_img = _crop(
        *_mosaic(NISAR_LAYER, NISAR_BEFORE, NISAR_ZOOM, "GoogleMapsCompatible_Level13"),
        NISAR_ZOOM,
    )
    nisar_after_img = _crop(
        *_mosaic(NISAR_LAYER, NISAR_AFTER, NISAR_ZOOM, "GoogleMapsCompatible_Level13"),
        NISAR_ZOOM,
    )

    mb = np.asarray(modis_before_img)
    ma = np.asarray(modis_after_img)
    nb = np.asarray(nisar_before_img)
    na = np.asarray(nisar_after_img)

    cloud = (mb.min(axis=2) > 190) | (ma.min(axis=2) > 190)
    modis_drop = (mb[:, :, 1].astype(int) - ma[:, :, 1].astype(int)) > 8
    modis_drop &= ~cloud

    both = _hv_mask(nb) & _hv_mask(na)
    nisar_drop = both & ((nb[:, :, 1].astype(int) - na[:, :, 1].astype(int)) > 12)

    # Paint the MODIS decline onto the NISAR grid. One MODIS pixel covers many NISAR pixels.
    candidate = np.zeros(nisar_drop.shape, dtype=bool)
    scale_y = mb.shape[0] / nb.shape[0]
    scale_x = mb.shape[1] / nb.shape[1]
    ys, xs = np.where(nisar_drop)
    for y, x in zip(ys.tolist(), xs.tolist()):
        my = min(mb.shape[0] - 1, int(y * scale_y))
        mx = min(mb.shape[1] - 1, int(x * scale_x))
        candidate[y, x] = bool(modis_drop[my, mx])
    # Drop isolated pixels. A kept pixel needs five hits in its 3x3 neighborhood.
    padded = np.pad(candidate, 1)
    neighbors = sum(padded[dy : dy + candidate.shape[0], dx : dx + candidate.shape[1]] for dy in range(3) for dx in range(3))
    alert = candidate & (neighbors >= 5)

    def _save(image: Image.Image, name: str, scale: int) -> None:
        image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(OUT / name)

    _save(modis_before_img, "modis-before.png", 24)
    _save(modis_after_img, "modis-after.png", 24)
    _save(nisar_before_img, "nisar-before.png", 4)
    _save(nisar_after_img, "nisar-after.png", 4)

    alert_rgba = np.zeros(nb.shape[:2] + (4,), dtype=np.uint8)
    alert_rgba[alert] = (220, 48, 32, 210)
    Image.fromarray(alert_rgba, "RGBA").resize(
        (alert_rgba.shape[1] * 4, alert_rgba.shape[0] * 4), Image.NEAREST
    ).save(OUT / "alert.png")

    nisar_m = 156543.03392 * math.cos(math.radians(-9.44)) / 2**NISAR_ZOOM
    modis_m = 156543.03392 * math.cos(math.radians(-9.44)) / 2**MODIS_ZOOM
    stats = {
        "west": BBOX[0],
        "south": BBOX[1],
        "east": BBOX[2],
        "north": BBOX[3],
        "modis_before": MODIS_BEFORE,
        "modis_after": MODIS_AFTER,
        "nisar_before": NISAR_BEFORE,
        "nisar_after": NISAR_AFTER,
        "modis_green_before": round(float(mb[:, :, 1][~cloud].mean()), 1) if (~cloud).any() else None,
        "modis_green_after": round(float(ma[:, :, 1][~cloud].mean()), 1) if (~cloud).any() else None,
        "modis_drop_pixels": int(modis_drop.sum()),
        "modis_pixels": int(mb.shape[0] * mb.shape[1]),
        "nisar_hv_before": round(float(nb[:, :, 1][both].mean()), 1) if both.any() else None,
        "nisar_hv_after": round(float(na[:, :, 1][both].mean()), 1) if both.any() else None,
        "nisar_drop_pixels": int(nisar_drop.sum()),
        "nisar_pixels": int(both.sum()),
        "alert_pixels": int(alert.sum()),
        "alert_ha": round(int(alert.sum()) * (nisar_m ** 2) / 10000.0, 1),
        "nisar_pixel_m": round(nisar_m),
        "modis_pixel_m": round(modis_m),
        "rain_mm": {
            "2016-09": _rain(2016, 9),
            "2025-09": _rain(2025, 9),
            "2026-09": _rain(2026, 9),
            "2026-10": _rain(2026, 10),
        },
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
