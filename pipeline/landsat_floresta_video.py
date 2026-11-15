"""Annual dry-season Landsat NDVI for the Floresta test box, 2010–2024.

One clearest August–November scene per year, Collection 2 Level-2.
OLI red and near-infrared are mapped back toward ETM+ (Roy et al. 2016)
before NDVI. The same color scale is used every year. The last frame is the
per-pixel slope. This is a small test, not the municipal RESTREND product.

    python3 -m pipeline.landsat_floresta_video
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import planetary_computer
import pystac_client
import rasterio
from PIL import Image, ImageDraw, ImageFont
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "floresta-landsat"
BBOX = (-38.58, -8.66, -38.46, -8.54)  # west, south, east, north
YEARS = range(2010, 2025)
DRY_MONTHS = {8, 9, 10, 11}
DST_CRS = "EPSG:32724"
RESOLUTION = 30
NDVI_LOW = 0.10
NDVI_HIGH = 0.70


def _grid():
    west, south, east, north = transform_bounds("EPSG:4326", DST_CRS, *BBOX)
    width = int(round((east - west) / RESOLUTION))
    height = int(round((north - south) / RESOLUTION))
    transform = from_origin(west, north, RESOLUTION, RESOLUTION)
    return transform, height, width


def _read(href: str, transform, shape, nearest: bool) -> np.ndarray:
    destination = np.full(shape, np.nan, dtype=np.float32)
    with rasterio.open(planetary_computer.sign(href)) as source:
        reproject(
            source=rasterio.band(source, 1),
            destination=destination,
            src_transform=source.transform,
            src_crs=source.crs,
            dst_transform=transform,
            dst_crs=DST_CRS,
            resampling=Resampling.nearest if nearest else Resampling.bilinear,
        )
    return destination


def _reflectance(raw: np.ndarray) -> np.ndarray:
    scaled = raw * 0.0000275 - 0.2
    scaled[(raw == 0) | ~np.isfinite(raw)] = np.nan
    return scaled


def _ndvi(item, transform, shape) -> np.ndarray:
    platform = item.properties.get("platform", "")
    red = _reflectance(_read(item.assets["red"].href, transform, shape, False))
    nir = _reflectance(_read(item.assets["nir08"].href, transform, shape, False))
    if platform in {"landsat-8", "landsat-9"}:
        red = (red - 0.0061) / 0.9047
        nir = (nir - 0.0412) / 0.8462
    qa = _read(item.assets["qa_pixel"].href, transform, shape, True)
    clear = np.isfinite(qa) & ((qa.astype(np.uint16) & 0b11111) == 0)
    valid = clear & np.isfinite(red) & np.isfinite(nir) & (red + nir > 0.05)
    ndvi = np.full(shape, np.nan, dtype=np.float32)
    ndvi[valid] = ((nir - red) / (nir + red))[valid]
    return ndvi


def _choose(items):
    rank = {"landsat-8": 0, "landsat-9": 1, "landsat-5": 2, "landsat-7": 3}
    return sorted(
        items,
        key=lambda item: (
            rank.get(item.properties.get("platform"), 9),
            item.properties.get("eo:cloud_cover", 100),
        ),
    )


def _year_ndvi(items, transform, shape) -> tuple[np.ndarray, list] | None:
    layers = []
    used = []
    for item in _choose(items):
        if len(layers) == 4:
            break
        candidate = _ndvi(item, transform, shape)
        covered = float(np.isfinite(candidate).mean())
        if covered < 0.3 or _striped(candidate):
            continue
        layers.append(candidate)
        used.append(item)
    if not layers:
        for item in _choose(items):
            candidate = _ndvi(item, transform, shape)
            if np.isfinite(candidate).mean() < 0.3:
                continue
            layers.append(candidate)
            used.append(item)
            if len(layers) == 4:
                break
    if not layers:
        return None
    return np.nanmedian(np.stack(layers), axis=0).astype(np.float32), used


def _striped(ndvi: np.ndarray) -> bool:
    row_valid = np.isfinite(ndvi).mean(axis=1)
    return float((row_valid < 0.25).mean()) > 0.12


def _paint(ndvi: np.ndarray, low: float, high: float) -> Image.Image:
    scale = np.clip((ndvi - low) / (high - low), 0, 1)
    red = 150 - scale * 120
    green = 78 + scale * 90
    blue = 36 - scale * 8
    image = np.zeros((*ndvi.shape, 4), dtype=np.uint8)
    valid = np.isfinite(ndvi)
    image[valid, 0] = red[valid]
    image[valid, 1] = green[valid]
    image[valid, 2] = blue[valid]
    image[valid, 3] = 255
    return Image.fromarray(image, "RGBA")


def _slope(stack: np.ndarray, years: np.ndarray) -> np.ndarray:
    mask = np.isfinite(stack)
    observed = np.where(mask, stack, 0.0)
    count = mask.sum(axis=0)
    when = years.astype(float)
    sum_x = (mask * when[:, None, None]).sum(axis=0)
    sum_x2 = (mask * (when ** 2)[:, None, None]).sum(axis=0)
    sum_y = observed.sum(axis=0)
    sum_xy = (observed * when[:, None, None]).sum(axis=0)
    denominator = count * sum_x2 - sum_x ** 2
    numerator = count * sum_xy - sum_x * sum_y
    result = np.full(count.shape, np.nan, dtype=np.float32)
    ok = (count >= 8) & (np.abs(denominator) > 1e-6)
    result[ok] = (numerator[ok] / denominator[ok]).astype(np.float32)
    return result


def _paint_slope(slope: np.ndarray) -> Image.Image:
    image = np.zeros((*slope.shape, 4), dtype=np.uint8)
    valid = np.isfinite(slope)
    loss = valid & (slope < -0.003)
    gain = valid & (slope > 0.003)
    image[loss] = (176, 48, 36, 230)
    image[gain] = (70, 130, 70, 200)
    steady = valid & ~loss & ~gain
    image[steady] = (180, 170, 140, 140)
    return Image.fromarray(image, "RGBA")


def _paint_anomaly(delta: np.ndarray, limit: float) -> Image.Image:
    scale = np.clip(delta / limit, -1, 1)
    image = np.zeros((*delta.shape, 4), dtype=np.uint8)
    valid = np.isfinite(delta)
    red = np.where(scale < 0, 176 + scale * 80, 90 + scale * 40)
    green = np.where(scale < 0, 70 + scale * 20, 78 + scale * 90)
    blue = np.where(scale < 0, 48, 40)
    image[valid, 0] = red[valid]
    image[valid, 1] = green[valid]
    image[valid, 2] = blue[valid]
    image[valid, 3] = 255
    return Image.fromarray(image, "RGBA")


def _labeled(frame: Image.Image, text: str, font, subfont) -> Image.Image:
    scaled = frame.resize((frame.width * 3, frame.height * 3), Image.Resampling.NEAREST)
    bar = 78
    canvas = Image.new("RGBA", (scaled.width, scaled.height + bar), (16, 20, 15, 255))
    canvas.paste(scaled, (0, bar))
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 8), text, font=font, fill=(244, 239, 230, 255))
    draw.text((16, 46), "Red is below the usual dry-season NDVI. Green is above it.", font=subfont, fill=(203, 187, 166, 255))
    return canvas


def _sheet(frames: list[Image.Image], trend: Image.Image, low: float, high: float, font) -> Image.Image:
    columns = 5
    cell_w, cell_h = frames[0].size
    rows = int(np.ceil(len(frames) / columns))
    gap = 8
    header = 64
    width = columns * cell_w + (columns + 1) * gap
    height = header + rows * cell_h + (rows + 1) * gap + cell_h + 36
    sheet = Image.new("RGBA", (width, height), (16, 20, 15, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, 8), "Floresta, PE — Landsat NDVI, dry season, 30 m", font=font, fill=(244, 239, 230, 255))
    draw.text((gap, 32), f"Same scale every year, NDVI {low:.2f} (tan) to {high:.2f} (green). Last panel: loss in red.", font=font, fill=(203, 187, 166, 255))
    for index, frame in enumerate(frames):
        column = index % columns
        row = index // columns
        x = gap + column * (cell_w + gap)
        y = header + gap + row * (cell_h + gap)
        sheet.paste(frame, (x, y))
    trend_row = header + gap + rows * (cell_h + gap)
    sheet.paste(trend.resize((cell_w, cell_h - 26), Image.Resampling.NEAREST), (gap, trend_row + 26))
    draw.text((gap, trend_row), "Loss (red) where NDVI falls faster than 0.003 per year", font=font, fill=(244, 239, 230, 255))
    return sheet


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    transform, height, width = _grid()
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=list(BBOX),
        datetime="2010-01-01/2024-12-31",
        query={"eo:cloud_cover": {"lt": 60}},
    )
    by_year: dict[int, list] = {year: [] for year in YEARS}
    for item in search.items():
        when = item.datetime
        if when.month not in DRY_MONTHS:
            continue
        by_year[when.year].append(item)

    records = []
    cube = []
    used_years = []
    for year in YEARS:
        built = _year_ndvi(by_year[year], transform, (height, width))
        if built is None:
            print(f"{year}: no clear dry-season scene")
            continue
        ndvi, used = built
        cube.append(ndvi)
        used_years.append(year)
        records.append({
            "year": year,
            "scenes": [
                {
                    "date": item.datetime.date().isoformat(),
                    "platform": item.properties.get("platform"),
                    "cloud_cover": item.properties.get("eo:cloud_cover"),
                }
                for item in used
            ],
            "ndvi_mean": round(float(np.nanmean(ndvi)), 3),
            "valid_fraction": round(float(np.isfinite(ndvi).mean()), 2),
        })
        print(f"{year}: {records[-1]['ndvi_mean']} from {len(used)} scenes")

    stack = np.stack(cube)
    years = np.array(used_years)
    np.savez_compressed(OUT / "cube.npz", stack=stack, years=years)
    finite = stack[np.isfinite(stack)]
    low, high = [float(value) for value in np.percentile(finite, [8, 92])]
    baseline = np.nanmedian(stack, axis=0)
    delta = stack - baseline
    limit = float(np.nanpercentile(np.abs(delta), 90))
    slope = _slope(stack, years)
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    note_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    frames = []
    for ndvi, year, shift in zip(stack, used_years, delta, strict=True):
        _paint(ndvi, low, high).save(OUT / f"{year}.png")
        mean_shift = float(np.nanmean(shift))
        word = "drier than usual" if mean_shift < -0.015 else "greener than usual" if mean_shift > 0.015 else "near the usual"
        frames.append(_labeled(_paint_anomaly(shift, limit), f"{year}   {word}", title_font, note_font))
    trend = _paint_slope(slope)
    trend.save(OUT / "trend.png")
    _sheet(
        [Image.open(OUT / f"{year}.png") for year in used_years],
        trend,
        low,
        high,
        small_font,
    ).save(OUT / "timelapse.png")
    playable = []
    for frame in frames:
        background = Image.new("RGB", frame.size, (16, 20, 15))
        background.paste(frame, mask=frame.split()[-1])
        playable.append(background)
    playable[0].save(
        OUT / "ndvi.gif",
        save_all=True,
        append_images=playable[1:],
        duration=900,
        loop=0,
    )
    summary = {
        "place": "Floresta, PE",
        "bbox": BBOX,
        "pixel_m": RESOLUTION,
        "scale": [round(low, 3), round(high, 3)],
        "scenes": records,
        "slope_ndvi_per_year": round(float(np.nanmean(slope)), 4),
        "loss_fraction": round(float(np.nanmean(slope < -0.003)), 2),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print("wrote", OUT)


def _rgb(item, transform, shape) -> np.ndarray:
    bands = [_reflectance(_read(item.assets[name].href, transform, shape, False)) for name in ("red", "green", "blue")]
    qa = _read(item.assets["qa_pixel"].href, transform, shape, True)
    clear = np.isfinite(qa) & ((qa.astype(np.uint16) & 0b11111) == 0)
    rgb = np.stack(bands).astype(np.float32)
    rgb[:, ~clear] = np.nan
    return rgb


def _paint_rgb(rgb: np.ndarray, low: float, high: float) -> Image.Image:
    """One scale for red, green and blue, so soil stays brown and vegetation stays dark green."""
    scale = np.clip((rgb - low) / (high - low), 0, 1)
    image = (scale.transpose(1, 2, 0) * 255).astype(np.uint8)
    image[~np.isfinite(rgb).all(axis=0)] = 16
    return Image.fromarray(image, "RGB")


def rgb_video() -> None:
    """True-color GIF from the same dry-season scenes already chosen for the NDVI cube."""
    summary = json.loads((OUT / "summary.json").read_text())
    wanted = {record["year"]: {scene["date"] for scene in record["scenes"]} for record in summary["scenes"]}
    transform, height, width = _grid()
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=list(BBOX),
        datetime="2010-01-01/2024-12-31",
        query={"eo:cloud_cover": {"lt": 60}},
    )
    chosen: dict[int, list] = {year: [] for year in wanted}
    for item in search.items():
        when = item.datetime
        if when.year in wanted and when.date().isoformat() in wanted[when.year]:
            chosen[when.year].append(item)

    layers = []
    years = []
    for year in sorted(wanted):
        scenes = []
        for item in chosen[year]:
            rgb = _rgb(item, transform, (height, width))
            if np.isfinite(rgb).all(axis=0).mean() < 0.2:
                continue
            scenes.append(rgb)
        if not scenes:
            print(f"{year}: no RGB")
            continue
        merged = np.nanmedian(np.stack(scenes), axis=0).astype(np.float32)
        layers.append(merged)
        years.append(year)
        print(f"{year}: {len(scenes)} scenes")

    cube = np.stack(layers)
    finite = cube[np.isfinite(cube)]
    low = float(np.percentile(finite, 2))
    high = float(np.percentile(finite, 98))
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    note_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    frames = []
    for rgb, year in zip(cube, years, strict=True):
        picture = _paint_rgb(rgb, low, high)
        picture.save(OUT / f"rgb-{year}.png")
        scaled = picture.resize((picture.width * 3, picture.height * 3), Image.Resampling.NEAREST)
        canvas = Image.new("RGB", (scaled.width, scaled.height + 72), (16, 20, 15))
        canvas.paste(scaled, (0, 72))
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 8), str(year), font=title_font, fill=(244, 239, 230))
        draw.text((16, 46), "Landsat cor verdadeira, mesma escala em todos os anos. Verde escuro é vegetação.", font=note_font, fill=(203, 187, 166))
        frames.append(canvas)
    frames[0].save(OUT / "rgb.gif", save_all=True, append_images=frames[1:], duration=900, loop=0)
    print("wrote", OUT / "rgb.gif", "stretch", round(low, 3), round(high, 3))


FOCUS_BBOX = (-38.5038, -8.5942, -38.4820, -8.5725)


def _grid_for(bbox):
    west, south, east, north = transform_bounds("EPSG:4326", DST_CRS, *bbox)
    width = int(round((east - west) / RESOLUTION))
    height = int(round((north - south) / RESOLUTION))
    return from_origin(west, north, RESOLUTION, RESOLUTION), height, width


def focus_september() -> None:
    """September-only true color on the hillside where the MODIS dry season already falls."""
    OUT.mkdir(parents=True, exist_ok=True)
    transform, height, width = _grid_for(FOCUS_BBOX)
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=list(FOCUS_BBOX),
        datetime="2010-01-01/2024-12-31",
        query={"eo:cloud_cover": {"lt": 40}},
    )
    by_year: dict[int, list] = {year: [] for year in YEARS}
    for item in search.items():
        if item.datetime.month == 9:
            by_year[item.datetime.year].append(item)

    layers = []
    years = []
    means = []
    for year in YEARS:
        scenes = []
        ndvis = []
        for item in _choose(by_year[year]):
            if len(scenes) == 3:
                break
            rgb = _rgb(item, transform, (height, width))
            ndvi = _ndvi(item, transform, (height, width))
            if np.isfinite(rgb).all(axis=0).mean() < 0.5 or _striped(ndvi):
                continue
            scenes.append(rgb)
            ndvis.append(ndvi)
        if not scenes:
            print(f"{year}: no clear September scene")
            continue
        merged = np.nanmedian(np.stack(scenes), axis=0).astype(np.float32)
        layers.append(merged)
        years.append(year)
        means.append(float(np.nanmean(np.nanmedian(np.stack(ndvis), axis=0))))
        print(f"{year}: {len(scenes)} scenes, NDVI {means[-1]:.3f}")

    cube = np.stack(layers)
    finite = cube[np.isfinite(cube)]
    low = float(np.percentile(finite, 2))
    high = float(np.percentile(finite, 98))
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    note_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    frames = []
    for rgb, year, mean in zip(cube, years, means, strict=True):
        picture = _paint_rgb(rgb, low, high)
        picture.save(OUT / f"foco-{year}.png")
        scaled = picture.resize((picture.width * 6, picture.height * 6), Image.Resampling.NEAREST)
        canvas = Image.new("RGB", (max(scaled.width, 720), scaled.height + 68), (16, 20, 15))
        canvas.paste(scaled, (0, 68))
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 6), f"{year}   setembro   NDVI {mean:.2f}", font=title_font, fill=(244, 239, 230))
        draw.text((12, 40), "Fora do riacho, onde o MODIS da estação seca já cai. Mesma escala.", font=note_font, fill=(203, 187, 166))
        frames.append(canvas)
    frames[0].save(OUT / "foco.gif", save_all=True, append_images=frames[1:], duration=900, loop=0)
    print("wrote", OUT / "foco.gif", "stretch", round(low, 3), round(high, 3))


if __name__ == "__main__":
    main()
