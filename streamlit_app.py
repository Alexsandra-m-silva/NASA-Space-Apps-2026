"""Compare-and-explain test for one municipality, Floresta.

The user draws a rectangle. The panel shows vegetation, rain, temperature
and the NISAR preview side by side. Matching or opposing signs are described
as convergence or divergence. The text does not assign a cause.

Rain and temperature are the NASA POWER point for the municipality. They do
not change inside the rectangle. The radar series is the public HV preview,
not gamma0 in dB.

    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import streamlit as st
from folium.plugins import Draw
from folium.raster_layers import ImageOverlay
from PIL import Image
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parent
CUBE = ROOT / "products" / "floresta_compare.npz"
META = ROOT / "products" / "floresta_compare.json"
OUTLINE = ROOT / "web" / "municipios" / "floresta" / "municipality.geojson"


def _slope(values: np.ndarray, when: np.ndarray, minimum: int) -> np.ndarray:
    mask = np.isfinite(values)
    observed = np.where(mask, values, 0.0)
    count = mask.sum(axis=0)
    sum_x = (mask * when[:, None, None]).sum(axis=0)
    sum_x2 = (mask * (when ** 2)[:, None, None]).sum(axis=0)
    sum_y = observed.sum(axis=0)
    sum_xy = (observed * when[:, None, None]).sum(axis=0)
    denominator = count * sum_x2 - sum_x ** 2
    numerator = count * sum_xy - sum_x * sum_y
    result = np.full(count.shape, np.nan, dtype=np.float32)
    ok = (count >= minimum) & (np.abs(denominator) > 1e-6)
    result[ok] = (numerator[ok] / denominator[ok]).astype(np.float32)
    return result


def _line_slope(frame: pd.DataFrame, x: str, y: str) -> float | None:
    kept = frame.dropna(subset=[y])
    if len(kept) < 4:
        return None
    return float(np.polyfit(kept[x].to_numpy(dtype=float), kept[y].to_numpy(dtype=float), 1)[0])


@st.cache_data(show_spinner=False)
def load():
    cube = np.load(CUBE)
    meta = json.loads(META.read_text())
    modis = cube["modis"].astype(np.float32)
    nisar = cube["nisar"].astype(np.float32)
    years = cube["modis_years"].astype(float)
    elapsed = np.arange(nisar.shape[0], dtype=float)
    modis_slope = _slope(modis, years, 8)
    nisar_slope = _slope(nisar, elapsed, 4)
    height, width = modis.shape[1:]
    image = np.zeros((height, width, 4), dtype=np.uint8)
    modis_down = np.isfinite(modis_slope) & (modis_slope < 0)
    nisar_down = np.isfinite(nisar_slope) & (nisar_slope < 0)
    both = modis_down & nisar_down
    image[modis_down & ~nisar_down] = (196, 92, 38, 210)
    image[both] = (176, 48, 36, 210)
    overlay = ROOT / "products" / "floresta_compare_overlay.png"
    Image.fromarray(image, "RGBA").save(overlay)
    return {
        "modis": modis,
        "nisar": nisar,
        "years": years,
        "dates": meta["nisar_dates"],
        "west": float(cube["west"]),
        "south": float(cube["south"]),
        "east": float(cube["east"]),
        "north": float(cube["north"]),
        "resolution": float(cube["resolution"]),
        "overlay": str(overlay),
        "both": both,
        "meta": meta,
    }


def _slices(box, data):
    west, south, east, north = box
    resolution = data["resolution"]
    height, width = data["modis"].shape[1:]
    col0 = int(np.floor((west - data["west"]) / resolution))
    col1 = int(np.ceil((east - data["west"]) / resolution))
    row0 = int(np.floor((data["north"] - north) / resolution))
    row1 = int(np.ceil((data["north"] - south) / resolution))
    col0 = max(0, min(width - 1, col0))
    col1 = max(col0 + 1, min(width, col1))
    row0 = max(0, min(height - 1, row0))
    row1 = max(row0 + 1, min(height, row1))
    return slice(row0, row1), slice(col0, col1)


def _means(stack: np.ndarray, rows, cols, keep: np.ndarray | None = None) -> list[float]:
    window = stack[:, rows, cols]
    if keep is not None:
        window = window[:, keep]
    means = []
    for layer in window:
        valid = layer[np.isfinite(layer)]
        means.append(float(valid.mean()) if valid.size else np.nan)
    return means


def _box_from_drawing(drawing) -> tuple[float, float, float, float] | None:
    if not drawing:
        return None
    geometry = drawing.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    if not coordinates:
        return None
    ring = coordinates[0]
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return min(lons), min(lats), max(lons), max(lats)


def _default_box(data) -> tuple[float, float, float, float]:
    west, south, east, north = data["west"], data["south"], data["east"], data["north"]
    return (
        west + 0.35 * (east - west),
        south + 0.35 * (north - south),
        west + 0.65 * (east - west),
        south + 0.65 * (north - south),
    )


def _reading(modis_slope, nisar_slope, slopes) -> str:
    parts = []
    if nisar_slope is None:
        parts.append("These red pixels do not have enough radar preview. The comparison uses MODIS only.")
    elif modis_slope is not None and modis_slope < 0 and nisar_slope < 0:
        parts.append("Among the red pixels, September MODIS and the radar preview both fall. The two vegetation signals converge.")
    elif modis_slope is not None and modis_slope > 0 and nisar_slope > 0:
        parts.append("Among the red pixels, September MODIS and the radar preview both rise. They converge on an increase, not a decline.")
    elif modis_slope is not None:
        parts.append("Among the red pixels, September MODIS and the radar preview point in opposite directions. They diverge: one covers many years, the other about four months of 2026.")
    rain_long = slopes["annual_precip_mm_per_year"]
    rain_window = slopes["modis_years_annual_precip_mm_per_year"]
    if modis_slope is not None and modis_slope < 0 and rain_long < 0 and rain_window > 0:
        parts.append("The vegetation decline lines up with the long rainfall record, but not with rainfall during the MODIS window. Those two rainfall records diverge from each other.")
    elif modis_slope is not None and modis_slope < 0 and rain_long < 0:
        parts.append("The vegetation decline and the long-record rainfall decline have the same sign.")
    elif modis_slope is not None and modis_slope < 0 and rain_window > 0:
        parts.append("Vegetation falls on the red pixels, while annual rainfall in the MODIS window does not. Those signals diverge.")
    parts.append("Temperature and rainfall are one point for the municipality, repeated for every rectangle. None of this is treated as a cause.")
    return " ".join(parts)


def _chart(frame: pd.DataFrame, x: str, y: str, color: str):
    kept = frame.dropna(subset=[y]).copy()
    if kept.empty:
        st.caption("No red pixels in this rectangle.")
        return
    if pd.api.types.is_datetime64_any_dtype(kept[x]):
        x_number = kept[x].astype("int64").to_numpy() / 1e9
        x_type = "temporal"
        axis = {"format": "%d %b", "labelAngle": -35, "labelOverlap": False}
    else:
        x_number = kept[x].to_numpy(dtype=float)
        x_type = "quantitative"
        axis = {"format": "d", "labelOverlap": "greedy"}
    slope, intercept = np.polyfit(x_number, kept[y].to_numpy(dtype=float), 1)
    kept["trend"] = slope * x_number + intercept
    low = float(min(kept[y].min(), kept["trend"].min()))
    high = float(max(kept[y].max(), kept["trend"].max()))
    pad = max((high - low) * 0.25, 0.5)
    y_scale = {"domain": [low - pad, high + pad]}
    spec = {
        "width": "container",
        "height": 160,
        "layer": [
            {
                "mark": {"type": "line", "point": True, "color": color, "strokeWidth": 2},
                "encoding": {"y": {"field": y, "type": "quantitative", "title": None, "scale": y_scale}},
            },
            {
                "mark": {"type": "line", "color": "#f7f4ea", "strokeDash": [5, 3], "strokeWidth": 1.5},
                "encoding": {"y": {"field": "trend", "type": "quantitative", "title": None, "scale": y_scale}},
            },
        ],
        "encoding": {"x": {"field": x, "type": x_type, "title": None, "axis": axis}},
    }
    st.vega_lite_chart(kept, spec, width="stretch")


def _map_legend(fmap) -> None:
    from branca.element import MacroElement
    from branca.element import Template

    legend = MacroElement()
    legend._template = Template(
        """
        {% macro html(this, kwargs) %}
        <div style="position:absolute; bottom:28px; left:12px; z-index:9999;
          background:rgba(16,20,15,0.92); color:#f7f4ea; padding:8px 10px;
          border-radius:6px; font:12px/1.45 sans-serif;">
          <div><span style="display:inline-block; width:11px; height:11px; background:#b03024; margin-right:6px; vertical-align:-1px;"></span>Red: decline in MODIS and in the radar preview</div>
          <div><span style="display:inline-block; width:11px; height:11px; background:#c45c26; margin-right:6px; vertical-align:-1px;"></span>Orange: decline in MODIS only</div>
        </div>
        {% endmacro %}
        """
    )
    fmap.get_root().add_child(legend)


def main() -> None:
    st.set_page_config(page_title="Compare signals — Floresta", layout="wide")
    if not CUBE.exists():
        st.error("Missing products/floresta_compare.npz. Run pipeline/compare_cube.py.")
        return
    data = load()
    slopes = data["meta"]["slopes"]
    if "box" not in st.session_state:
        st.session_state.box = _default_box(data)

    map_column, side = st.columns([1.35, 1], gap="medium")
    with map_column:
        st.markdown("**Floresta, PE.** Draw a rectangle. The charts use only the red pixels inside it.")
        west, south, east, north = st.session_state.box
        fmap = folium.Map(location=[(south + north) / 2, (west + east) / 2], zoom_start=10, tiles=None)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri, Maxar",
            name="Satellite",
        ).add_to(fmap)
        ImageOverlay(
            image=data["overlay"],
            bounds=[[data["south"], data["west"]], [data["north"], data["east"]]],
            opacity=0.9,
            pixelated=True,
        ).add_to(fmap)
        if OUTLINE.exists():
            folium.GeoJson(
                json.loads(OUTLINE.read_text()),
                style_function=lambda _feature: {"color": "#fff4d6", "weight": 1.6, "fill": False},
            ).add_to(fmap)
        folium.Rectangle(bounds=[[south, west], [north, east]], color="#f0c36a", weight=2, fill=False).add_to(fmap)
        Draw(
            export=False,
            draw_options={
                "rectangle": True,
                "polyline": False,
                "polygon": False,
                "circle": False,
                "marker": False,
                "circlemarker": False,
            },
        ).add_to(fmap)
        fmap.fit_bounds([[data["south"], data["west"]], [data["north"], data["east"]]])
        _map_legend(fmap)
        drawn = st_folium(fmap, height=560, use_container_width=True, returned_objects=["last_active_drawing"], key="floresta")
        chosen = _box_from_drawing((drawn or {}).get("last_active_drawing"))
        if chosen:
            st.session_state.box = chosen
            west, south, east, north = chosen

    rows, cols = _slices((west, south, east, north), data)
    red = data["both"][rows, cols]
    red_pixels = int(red.sum())
    modis_frame = pd.DataFrame({"year": data["years"], "green": _means(data["modis"], rows, cols, red)})
    day_index = np.arange(len(data["dates"]), dtype=float)
    nisar_frame = pd.DataFrame(
        {"day": day_index, "date": pd.to_datetime(data["dates"]), "green": _means(data["nisar"], rows, cols, red)}
    )
    annual = pd.DataFrame(data["meta"]["annual"])
    modis_slope = _line_slope(modis_frame, "year", "green")
    nisar_slope = _line_slope(nisar_frame.rename(columns={"day": "year"}), "year", "green")

    with side:
        st.markdown("**Compare the signals**")
        st.caption("Red pixels only. The dashed line is the linear tendency. Agreement is not a cause.")
        left, right = st.columns(2)
        with left:
            st.caption("Vegetation — MODIS, September, color scale")
            _chart(modis_frame, "year", "green", "#c45c26")
        with right:
            st.caption("Radar — HV preview, not gamma0")
            _chart(nisar_frame, "date", "green", "#d4a830")
        left, right = st.columns(2)
        with left:
            st.caption("Annual rainfall at the point, mm")
            _chart(annual, "year", "precip_mm", "#7eb6d6")
        with right:
            st.caption("Annual temperature at the point, °C")
            _chart(annual, "year", "temp_c", "#f0c36a")
        if red_pixels == 0:
            st.info("This rectangle has no red pixels. Draw over the red area to compare the signals.")
        else:
            st.info(_reading(modis_slope, nisar_slope, slopes))
        orbit = data["meta"]["orbit"].replace("descendente", "descending").replace("quadro", "frame")
        st.caption(
            f"Rectangle: {red_pixels} red pixels used in the charts. "
            f"Orbit {orbit}."
        )


main()
