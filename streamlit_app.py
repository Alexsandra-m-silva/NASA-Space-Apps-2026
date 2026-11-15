"""Comparar e explicar — degradação da vegetação pelo método do NDVI (5 municípios).

O usuário escolhe o município e desenha um retângulo. O painel mostra, para os pixels
dentro dele: NDVI anual (MODIS 2001–2024), a tendência do NDVI descontada a chuva
(RESTREND, com teste de Mann-Kendall), o radar NISAR (HV calibrado em dB, 2026),
a chuva e a temperatura do município. Sinais iguais ou opostos são descritos como
convergência ou divergência. O texto não atribui causa.

Cubos: products/<slug>_ndvi.npz e .json, gerados por pipeline/cubos_ndvi.py.

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
from scipy.stats import norm
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parent
PRODUCTS = ROOT / "products"
INDEX = PRODUCTS / "ndvi_index.json"
COLORS = {"ambos": (176, 48, 36, 215), "so_ndvi": (196, 92, 38, 210), "melhora": (88, 140, 84, 150)}


# ---------------------------------------------------------------- estatística por pixel
def _slope(values: np.ndarray, when: np.ndarray, minimum: int) -> np.ndarray:
    """Inclinação linear por pixel, ignorando faltas."""
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


def _restrend(ndvi: np.ndarray, rain: np.ndarray, years: np.ndarray):
    """Resíduo do NDVI depois de descontar a chuva; tendência de Sen e Mann-Kendall do resíduo."""
    n_years, h, w = ndvi.shape
    y, r = ndvi.reshape(n_years, -1), rain.reshape(n_years, -1)
    ok = np.isfinite(y) & np.isfinite(r)
    n = ok.sum(0)
    rm = np.where(ok, r, 0).sum(0) / np.maximum(n, 1)
    ym = np.where(ok, y, 0).sum(0) / np.maximum(n, 1)
    b = np.where(ok, (r - rm) * (y - ym), 0).sum(0) / np.maximum(np.where(ok, (r - rm) ** 2, 0).sum(0), 1e-9)
    resid = np.where(ok, y - (ym + b * (r - rm)), np.nan)
    i, j = np.triu_indices(n_years, 1)
    diff = resid[j] - resid[i]
    s = np.nansum(np.sign(diff), axis=0)
    var = n * (n - 1) * (2 * n + 5) / 18.0
    z = np.where(s > 0, (s - 1), np.where(s < 0, (s + 1), 0)) / np.sqrt(np.maximum(var, 1e-9))
    p = 2 * (1 - norm.cdf(np.abs(z)))
    with np.errstate(all="ignore"):
        sen = np.nanmedian(diff / (years[j] - years[i])[:, None], axis=0)
    enough = n >= 15
    shape = (h, w)
    return (resid.reshape(n_years, h, w), np.where(enough, sen, np.nan).reshape(shape),
            np.where(enough, p, np.nan).reshape(shape))


@st.cache_data(show_spinner="Computing the per-pixel trends…")
def load(slug: str):
    cube = np.load(PRODUCTS / f"{slug}_ndvi.npz")
    meta = json.loads((PRODUCTS / f"{slug}_ndvi.json").read_text(encoding="utf-8"))
    ndvi, rain = cube["ndvi"].astype(np.float32), cube["chuva"].astype(np.float32)
    hv = cube["hv_db"].astype(np.float32)
    years = cube["anos"].astype(float)
    dates = pd.to_datetime(meta["datas_nisar"])
    days = ((dates - dates[0]).days.to_numpy(dtype=float)) if len(dates) else np.zeros(0)
    resid, sen, p = _restrend(ndvi, rain, years)
    hv_slope = _slope(hv, days, 4) if len(days) else np.full(sen.shape, np.nan, np.float32)
    # Na estação seca o HV cai em quase todo o município (a vegetação seca). Por isso o critério é
    # relativo: o pixel cai mais rápido que a mediana do município no mesmo período.
    hv_med = float(np.nanmedian(hv_slope)) if np.isfinite(hv_slope).any() else np.nan
    degradado = np.isfinite(sen) & (sen < 0) & (p < 0.05)
    melhora = np.isfinite(sen) & (sen > 0) & (p < 0.05)
    radar_queda = np.isfinite(hv_slope) & (hv_slope < hv_med)
    ambos = degradado & radar_queda
    image = np.zeros(sen.shape + (4,), dtype=np.uint8)
    image[melhora] = COLORS["melhora"]
    image[degradado & ~radar_queda] = COLORS["so_ndvi"]
    image[ambos] = COLORS["ambos"]
    overlay = PRODUCTS / f"{slug}_ndvi_overlay.png"
    Image.fromarray(image, "RGBA").save(overlay)
    return {
        "ndvi": ndvi, "resid": resid, "hv": hv, "years": years, "dates": list(meta["datas_nisar"]),
        "west": float(cube["west"]), "south": float(cube["south"]), "east": float(cube["east"]),
        "north": float(cube["north"]), "resolution": float(cube["resolution"]), "overlay": str(overlay),
        "degradado": degradado, "ambos": ambos, "melhora": melhora, "meta": meta, "hv_med_dia": hv_med,
        "contagem": {"degradado": int(degradado.sum()), "ambos": int(ambos.sum()), "melhora": int(melhora.sum()),
                     "validos": int(np.isfinite(sen).sum())},
    }


# ---------------------------------------------------------------- retângulo
def _slices(box, data):
    west, south, east, north = box
    resolution = data["resolution"]
    height, width = data["ndvi"].shape[1:]
    col0 = max(0, min(width - 1, int(np.floor((west - data["west"]) / resolution))))
    col1 = max(col0 + 1, min(width, int(np.ceil((east - data["west"]) / resolution))))
    row0 = max(0, min(height - 1, int(np.floor((data["north"] - north) / resolution))))
    row1 = max(row0 + 1, min(height, int(np.ceil((data["north"] - south) / resolution))))
    return slice(row0, row1), slice(col0, col1)


def _means(stack: np.ndarray, rows, cols, keep: np.ndarray | None = None) -> list[float]:
    window = stack[:, rows, cols]
    if keep is not None:
        window = window[:, keep]
    out = []
    for layer in window:
        valid = layer[np.isfinite(layer)]
        out.append(float(valid.mean()) if valid.size else np.nan)
    return out


def _box_from_drawing(drawing):
    if not drawing:
        return None
    ring = ((drawing.get("geometry") or {}).get("coordinates") or [[]])[0]
    if not ring:
        return None
    lons, lats = [q[0] for q in ring], [q[1] for q in ring]
    return min(lons), min(lats), max(lons), max(lats)


def _default_box(data):
    west, south, east, north = data["west"], data["south"], data["east"], data["north"]
    return (west + 0.3 * (east - west), south + 0.3 * (north - south),
            west + 0.7 * (east - west), south + 0.7 * (north - south))


def _line_slope(frame: pd.DataFrame, x: str, y: str):
    kept = frame.dropna(subset=[y])
    if len(kept) < 4:
        return None
    xs = kept[x]
    xs = (xs - xs.min()).dt.days.to_numpy(float) if pd.api.types.is_datetime64_any_dtype(xs) else xs.to_numpy(float)
    return float(np.polyfit(xs, kept[y].to_numpy(float), 1)[0])


# ---------------------------------------------------------------- texto e gráficos
def _leitura(resid_slope, hv_slope, rain_slope, temp_slope, usou_degradados: bool) -> str:
    alvo = "On the degraded pixels in the rectangle" if usou_degradados else "In the rectangle"
    partes = []
    if resid_slope is None:
        partes.append(f"{alvo}, there are not enough NDVI years for a trend.")
    elif hv_slope is None:
        partes.append(f"{alvo}, there are not enough radar dates. The reading uses NDVI only.")
    elif resid_slope < 0 and hv_slope < 0:
        partes.append(f"{alvo}, rainfall-adjusted NDVI has fallen since 2001 and, in 2026, NISAR falls faster "
                      "than is typical for this municipality in the dry season. The two vegetation signals agree.")
    elif resid_slope > 0 and hv_slope >= 0:
        partes.append(f"{alvo}, rainfall-adjusted NDVI is rising and the radar falls less than is typical for this municipality. "
                      "They agree on more persistent vegetation, and they do not agree on a decline.")
    else:
        partes.append(f"{alvo}, rainfall-adjusted NDVI and the radar (compared with what is typical for the municipality) point in "
                      "opposite directions. They diverge: one covers 24 years, the other a few months of the 2026 dry season.")
    if resid_slope is not None and resid_slope < 0:
        if rain_slope is not None and rain_slope >= 0:
            partes.append("The vegetation decline shows up even while municipal rainfall is steady or rising.")
        if temp_slope is not None and temp_slope > 0:
            partes.append("Over the same period, the municipality's mean temperature rises.")
    partes.append("Rain and temperature are the municipal average, the same for every rectangle. "
                  "Agreement between signals is not proof of a cause.")
    return " ".join(partes)


def _chart(frame: pd.DataFrame, x: str, y: str, color: str):
    kept = frame.dropna(subset=[y]).copy()
    if kept.empty:
        st.caption("No data in this rectangle.")
        return
    if pd.api.types.is_datetime64_any_dtype(kept[x]):
        x_number = kept[x].astype("int64").to_numpy() / 1e9
        x_type, axis = "temporal", {"format": "%d %b", "labelAngle": -35, "labelOverlap": False}
    else:
        x_number = kept[x].to_numpy(dtype=float)
        x_type, axis = "quantitative", {"format": "d", "labelOverlap": "greedy"}
    slope, intercept = np.polyfit(x_number, kept[y].to_numpy(dtype=float), 1)
    kept["tendencia"] = slope * x_number + intercept
    low = float(min(kept[y].min(), kept["tendencia"].min()))
    high = float(max(kept[y].max(), kept["tendencia"].max()))
    pad = max((high - low) * 0.25, 1e-3)
    scale = {"domain": [low - pad, high + pad]}
    spec = {"width": "container", "height": 150, "layer": [
        {"mark": {"type": "line", "point": True, "color": color, "strokeWidth": 2},
         "encoding": {"y": {"field": y, "type": "quantitative", "title": None, "scale": scale}}},
        {"mark": {"type": "line", "color": "#f7f4ea", "strokeDash": [5, 3], "strokeWidth": 1.5},
         "encoding": {"y": {"field": "tendencia", "type": "quantitative", "title": None, "scale": scale}}}],
        "encoding": {"x": {"field": x, "type": x_type, "title": None, "axis": axis}}}
    st.vega_lite_chart(kept, spec, width="stretch")


def _legenda(fmap) -> None:
    from branca.element import MacroElement, Template

    el = MacroElement()
    item = lambda c, t: (f'<div><span style="display:inline-block;width:11px;height:11px;background:{c};'
                         f'margin-right:6px;vertical-align:-1px;"></span>{t}</div>')
    el._template = Template(
        '{% macro html(this, kwargs) %}<div style="position:absolute;bottom:28px;left:12px;z-index:9999;'
        'background:rgba(16,20,15,0.92);color:#f7f4ea;padding:8px 10px;border-radius:6px;font:12px/1.45 sans-serif;">'
        + item("#b03024", "Red: rainfall-adjusted NDVI declining, and radar falling faster than typical")
        + item("#c45c26", "Orange: NDVI declining, radar within the typical range")
        + item("#588c54", "Green: NDVI improving")
        + "</div>{% endmacro %}")
    fmap.get_root().add_child(el)


# ---------------------------------------------------------------- página
def main() -> None:
    st.set_page_config(page_title="Compare and explain — vegetation degradation", layout="wide")
    if not INDEX.exists():
        st.error("The cubes in products/ are missing. Run: python -m pipeline.cubos_ndvi build")
        return
    lugares = json.loads(INDEX.read_text(encoding="utf-8"))
    nomes = {f"{p['municipio']} / {p['uf']}": p["slug"] for p in lugares}
    escolha = st.selectbox("Municipality", list(nomes), index=next((i for i, k in enumerate(nomes) if k.startswith("Floresta")), 0))
    slug = nomes[escolha]
    data = load(slug)
    if st.session_state.get("slug") != slug:
        st.session_state.slug = slug
        st.session_state.box = _default_box(data)

    c = data["contagem"]
    total = max(c["validos"], 1)
    m1, m2, m3, m4 = st.columns(4)
    pct = lambda v: f"{100 * v / total:.1f}% of the area"
    m1.metric("NDVI declining (rainfall removed)", pct(c["degradado"]))
    m2.metric("Declining, and radar falling faster than typical", pct(c["ambos"]))
    m3.metric("NDVI improving", pct(c["melhora"]))
    m4.metric("NISAR passes", f"{len(data['dates'])}")

    map_column, side = st.columns([1.35, 1], gap="medium")
    with map_column:
        st.markdown(f"**{escolha}.** Draw a rectangle. The charts use the degraded pixels inside it "
                    "(or every pixel, if none are degraded).")
        west, south, east, north = st.session_state.box
        fmap = folium.Map(location=[(south + north) / 2, (west + east) / 2], zoom_start=10, tiles=None)
        folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                         attr="Esri, Maxar", name="Satellite").add_to(fmap)
        ImageOverlay(image=data["overlay"], bounds=[[data["south"], data["west"]], [data["north"], data["east"]]],
                     opacity=0.9, pixelated=True).add_to(fmap)
        outline = ROOT / "web" / "municipios" / slug / "municipality.geojson"
        if outline.exists():
            folium.GeoJson(json.loads(outline.read_text(encoding="utf-8")),
                           style_function=lambda _f: {"color": "#fff4d6", "weight": 1.6, "fill": False}).add_to(fmap)
        folium.Rectangle(bounds=[[south, west], [north, east]], color="#f0c36a", weight=2, fill=False).add_to(fmap)
        Draw(export=False, draw_options={"rectangle": True, "polyline": False, "polygon": False, "circle": False,
                                         "marker": False, "circlemarker": False}).add_to(fmap)
        fmap.fit_bounds([[data["south"], data["west"]], [data["north"], data["east"]]])
        _legenda(fmap)
        drawn = st_folium(fmap, height=560, use_container_width=True, returned_objects=["last_active_drawing"], key=f"mapa_{slug}")
        chosen = _box_from_drawing((drawn or {}).get("last_active_drawing"))
        if chosen:
            st.session_state.box = chosen
            west, south, east, north = chosen

    rows, cols = _slices((west, south, east, north), data)
    sel = data["degradado"][rows, cols]
    usou_degradados = bool(sel.sum())
    keep = sel if usou_degradados else None
    ndvi_df = pd.DataFrame({"ano": data["years"], "ndvi": _means(data["ndvi"], rows, cols, keep)})
    resid_df = pd.DataFrame({"ano": data["years"], "residuo": _means(data["resid"], rows, cols, keep)})
    radar_df = pd.DataFrame({"data": pd.to_datetime(data["dates"]), "hv": _means(data["hv"], rows, cols, keep)}) \
        if data["dates"] else pd.DataFrame({"data": pd.to_datetime([]), "hv": []})
    clima = pd.DataFrame(data["meta"]["clima_anual"])
    clima_janela = clima[clima.ano >= 2001]

    with side:
        st.markdown("**Signals inside the rectangle**")
        st.caption("Dashed line: linear trend. Agreement is not a cause.")
        a, b = st.columns(2)
        with a:
            st.caption("Annual NDVI — MODIS, 2001–2024")
            _chart(ndvi_df, "ano", "ndvi", "#7fb069")
        with b:
            st.caption("Rainfall-adjusted NDVI (residual)")
            _chart(resid_df, "ano", "residuo", "#c45c26")
        a, b = st.columns(2)
        with a:
            med = data["hv_med_dia"] * 30 if np.isfinite(data["hv_med_dia"]) else float("nan")
            st.caption(f"NISAR radar — HV (dB), 2026 · typical for the municipality: {med:+.2f} dB/month")
            _chart(radar_df, "data", "hv", "#d4a830")
        with b:
            st.caption("Municipal annual rainfall (mm)")
            _chart(clima, "ano", "chuva_mm", "#7eb6d6")
        st.caption("Municipal mean annual temperature (°C)")
        _chart(clima, "ano", "temp_c", "#f0c36a")
        hv_sel = _line_slope(radar_df, "data", "hv")
        hv_rel = None if hv_sel is None or not np.isfinite(data["hv_med_dia"]) else hv_sel - data["hv_med_dia"]
        st.info(_leitura(_line_slope(resid_df, "ano", "residuo"), hv_rel,
                         _line_slope(clima_janela, "ano", "chuva_mm"), _line_slope(clima_janela, "ano", "temp_c"),
                         usou_degradados))
        n_pix = int(sel.sum()) if usou_degradados else int(np.isfinite(data["ndvi"][0][rows, cols]).sum())
        orbita = str(data["meta"].get("orbita") or "—").replace("descendente", "descending").replace("quadro", "frame")
        st.caption(f"Pixels used: {n_pix} ({'degraded' if usou_degradados else 'all'}), grid of about 1.1 km. "
                   f"Radar: NISAR L2 GCOV, orbit/frame {orbita}, calibrated gamma0. "
                   "NDVI: MODIS MOD13Q1. Rain: CHIRPS. Temperature: ERA5-Land. Degradation = a negative trend in "
                   "rainfall-adjusted NDVI with Mann-Kendall p < 0.05.")


main()
