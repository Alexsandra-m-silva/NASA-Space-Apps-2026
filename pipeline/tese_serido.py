"""Teste da tese no núcleo do Seridó: o NISAR vê a degradação que o histórico mostra?

Passos (cada um grava em data/processed/tese_serido/ e pode ser rodado de novo):
    python -m pipeline.tese_serido points           # sorteia pontos no núcleo
    python -m pipeline.tese_serido appeears-submit  # pede NDVI MODIS 2001–2025 + cobertura MCD12Q1
    python -m pipeline.tese_serido appeears-fetch   # baixa quando o AppEEARS terminar
    python -m pipeline.tese_serido chirps           # chuva anual CHIRPS nos pontos
    python -m pipeline.tese_serido nisar            # HV do NISAR GCOV nos pontos
    python -m pipeline.tese_serido analyze          # rótulo de referência x NISAR
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")

NUCLEO = "serido"
N_POINTS = 1000
SEED = 42
OUT = DATA_PROCESSED / f"tese_{NUCLEO}"
POINTS = OUT / "points.csv"
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api"
YEARS = range(2001, 2026)


# ---------------------------------------------------------------- pontos
def points() -> None:
    from shapely.geometry import Point, shape
    from shapely.ops import unary_union

    gj = json.loads((DATA_PROCESSED / "nucleos_municipios.geojson").read_text(encoding="utf-8"))
    polys = [shape(f["geometry"]) for f in gj["features"] if f["properties"]["nucleo"] == NUCLEO]
    area = unary_union(polys)
    rng = np.random.default_rng(SEED)
    minx, miny, maxx, maxy = area.bounds
    pts = []
    while len(pts) < N_POINTS:
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if area.contains(Point(x, y)):
            pts.append((len(pts), round(x, 6), round(y, 6)))
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(pts, columns=["id", "lon", "lat"]).to_csv(POINTS, index=False)
    print(POINTS, len(pts), "bbox", [round(v, 3) for v in area.bounds])


# ---------------------------------------------------------------- AppEEARS
def _token() -> str:
    r = requests.post(f"{APPEEARS}/login", auth=(os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"]), timeout=60)
    r.raise_for_status()
    return r.json()["token"]


def appeears_submit() -> None:
    pts = pd.read_csv(POINTS)
    task = {
        "task_type": "point",
        "task_name": f"tese_{NUCLEO}_ndvi",
        "params": {
            "dates": [{"startDate": "01-01-2001", "endDate": "12-31-2025"}],
            "layers": [
                {"product": "MOD13Q1.061", "layer": "_250m_16_days_NDVI"},
                {"product": "MOD13Q1.061", "layer": "_250m_16_days_pixel_reliability"},
                {"product": "MCD12Q1.061", "layer": "LC_Type1"},
            ],
            "coordinates": [{"id": str(r.id), "latitude": r.lat, "longitude": r.lon} for r in pts.itertuples()],
        },
    }
    r = requests.post(f"{APPEEARS}/task", json=task, headers={"Authorization": f"Bearer {_token()}"}, timeout=120)
    print(r.status_code, r.text[:500])
    r.raise_for_status()
    (OUT / "appeears_task.json").write_text(r.text, encoding="utf-8")


def appeears_fetch(wait: bool = True) -> None:
    task_id = json.loads((OUT / "appeears_task.json").read_text())["task_id"]
    headers = {"Authorization": f"Bearer {_token()}"}
    while True:
        st = requests.get(f"{APPEEARS}/task/{task_id}", headers=headers, timeout=60).json()
        print(time.strftime("%H:%M:%S"), st.get("status"), st.get("progress", {}).get("summary"))
        if st.get("status") == "done" or not wait:
            break
        if st.get("status") == "error":
            raise SystemExit(st)
        time.sleep(60)
    if st.get("status") != "done":
        return
    bundle = requests.get(f"{APPEEARS}/bundle/{task_id}", headers=headers, timeout=60).json()
    for f in bundle["files"]:
        if f["file_name"].endswith(".csv"):
            data = requests.get(f"{APPEEARS}/bundle/{task_id}/{f['file_id']}", headers=headers, timeout=600)
            (OUT / f["file_name"].split("/")[-1]).write_bytes(data.content)
            print("baixado", f["file_name"])


# ---------------------------------------------------------------- CHIRPS
def chirps() -> None:
    import rasterio

    pts = pd.read_csv(POINTS)
    coords = list(zip(pts.lon, pts.lat))
    cols = {}
    for y in YEARS:
        url = f"/vsicurl/https://data.chc.ucsb.edu/products/CHIRPS/v2.0/global_annual/tifs/chirps-v2.0.{y}.tif"
        try:
            with rasterio.open(url) as src:
                cols[y] = [v[0] for v in src.sample(coords)]
            print(y, "ok")
        except Exception as e:  # ano ainda não publicado
            print(y, "indisponível:", type(e).__name__)
    df = pd.DataFrame(cols, index=pts.id)
    df[df < 0] = np.nan
    df.to_csv(OUT / "chirps_annual.csv")


# ---------------------------------------------------------------- NISAR
NISAR_PRODUCT = "NISAR_L2_GCOV_PROVISIONAL_V1"
NISAR_TRACK_FRAME = "_059_A_174_"  # mesma geometria em todas as datas
NISAR_GROUP = "science/LSAR/GCOV/grids/frequencyA"
HALF_WINDOW = 6  # 13 x 13 px de 20 m ~ pixel MODIS de 250 m


def nisar() -> None:
    import earthaccess
    import h5py
    from pyproj import Transformer

    earthaccess.login(strategy="environment")
    pts = pd.read_csv(POINTS)
    pad = 0.02
    bbox = (pts.lon.min() - pad, pts.lat.min() - pad, pts.lon.max() + pad, pts.lat.max() + pad)
    grans = [g for g in earthaccess.search_data(short_name=NISAR_PRODUCT, bounding_box=bbox, count=500)
             if NISAR_TRACK_FRAME in g["umm"]["GranuleUR"] and "_DHDH_" in g["umm"]["GranuleUR"]]
    print(len(grans), "cenas", NISAR_TRACK_FRAME)
    cache = OUT / "nisar"
    cache.mkdir(exist_ok=True)

    for g in grans:
        ur = g["umm"]["GranuleUR"]
        date = ur.split("_")[11][:8]
        out = cache / f"{date}.csv"
        if out.exists():
            continue
        f = earthaccess.open([g])[0]
        with h5py.File(f, "r") as h:
            grp = h[NISAR_GROUP]
            x, y = grp["xCoordinates"][()], grp["yCoordinates"][()]
            epsg = int(grp["projection"].attrs["epsg_code"])
            tr = Transformer.from_crs(4326, epsg, always_xy=True)
            px, py = tr.transform(pts.lon.values, pts.lat.values)
            dx, dy = x[1] - x[0], y[1] - y[0]
            col = np.round((px - x[0]) / dx).astype(int)
            row = np.round((py - y[0]) / dy).astype(int)
            inside = (col >= HALF_WINDOW) & (col < len(x) - HALF_WINDOW) & (row >= HALF_WINDOW) & (row < len(y) - HALF_WINDOW)
            r0, r1 = row[inside].min() - HALF_WINDOW, row[inside].max() + HALF_WINDOW + 1
            c0, c1 = col[inside].min() - HALF_WINDOW, col[inside].max() + HALF_WINDOW + 1
            hv = grp["HVHV"][r0:r1, c0:c1]
            hh = grp["HHHH"][r0:r1, c0:c1]
            mask = grp["mask"][r0:r1, c0:c1]
        valid = (mask > 0) & (mask < 255) & np.isfinite(hv) & (hv > 0) & np.isfinite(hh) & (hh > 0)
        rows = []
        for pid, ok, rr, cc in zip(pts.id, inside, row - r0, col - c0):
            if not ok:
                rows.append((pid, np.nan, np.nan, 0))
                continue
            sl = np.s_[rr - HALF_WINDOW: rr + HALF_WINDOW + 1, cc - HALF_WINDOW: cc + HALF_WINDOW + 1]
            v = valid[sl]
            n = int(v.sum())
            if n < 0.5 * v.size:
                rows.append((pid, np.nan, np.nan, n))
                continue
            # média em potência linear, depois dB
            rows.append((pid, 10 * np.log10(hv[sl][v].mean()), 10 * np.log10(hh[sl][v].mean()), n))
        pd.DataFrame(rows, columns=["id", "hv_db", "hh_db", "n_valid"]).to_csv(out, index=False)
        print(date, "pontos válidos:", int(np.isfinite([r[1] for r in rows]).sum()))


# ---------------------------------------------------------------- análise
IGBP = {1: "Floresta perene acicul.", 2: "Floresta perene latif.", 6: "Arbustiva fechada", 7: "Arbustiva aberta",
        8: "Savana arborizada", 9: "Savana", 10: "Campo", 12: "Agricultura", 13: "Urbano",
        14: "Mosaico agric./natural", 16: "Solo exposto", 17: "Água"}


def _reference() -> pd.DataFrame:
    from scipy.stats import kendalltau, theilslopes

    files = sorted(OUT.glob("*MOD13Q1*results.csv"))
    if not files:
        raise SystemExit("Rode appeears-fetch primeiro.")
    m = pd.read_csv(files[0])
    ndvi_col = [c for c in m.columns if c.endswith("_250m_16_days_NDVI")][0]
    rel_col = [c for c in m.columns if c.endswith("_pixel_reliability")][0]
    m = m[m[rel_col].isin([0, 1])]
    m["year"] = pd.to_datetime(m["Date"]).dt.year
    ndvi = m.groupby(["ID", "year"])[ndvi_col].mean().unstack()  # NDVI já em escala 0–1 no AppEEARS
    rain = pd.read_csv(OUT / "chirps_annual.csv", index_col=0)
    rain.columns = rain.columns.astype(int)
    years = [y for y in ndvi.columns if y in rain.columns]

    out = []
    for pid in ndvi.index:
        n, r = ndvi.loc[pid, years].to_numpy(float), rain.loc[pid, years].to_numpy(float)
        ok = np.isfinite(n) & np.isfinite(r)
        if ok.sum() < 15:
            continue
        yrs = np.asarray(years)[ok]
        b, a = np.polyfit(r[ok], n[ok], 1)
        resid = n[ok] - (a + b * r[ok])
        slope = theilslopes(resid, yrs)[0]
        tau, p = kendalltau(yrs, resid)
        out.append({"id": pid, "resid_slope": slope, "resid_tau": tau, "resid_p": p,
                    "ndvi_mean": np.nanmean(n), "ndvi_recent": np.nanmean(n[ok][-3:]),
                    "ndvi_raw_slope": theilslopes(n[ok], yrs)[0], "ndvi_rain_r": np.corrcoef(r[ok], n[ok])[0, 1]})
    ref = pd.DataFrame(out)
    ref["ref_class"] = np.select(
        [(ref.resid_slope < 0) & (ref.resid_p < 0.05), (ref.resid_slope > 0) & (ref.resid_p < 0.05)],
        ["degradado", "melhora"], "estavel")

    lc_files = sorted(OUT.glob("*MCD12Q1*results.csv"))
    if lc_files:
        lc = pd.read_csv(lc_files[0])
        lc_col = [c for c in lc.columns if c.endswith("LC_Type1")][0]
        lc["year"] = pd.to_datetime(lc["Date"]).dt.year
        last = lc.sort_values("year").groupby("ID").last()[lc_col]
        ref["lc"] = ref["id"].map(last)
    return ref


def _auc(score: np.ndarray, label: np.ndarray) -> tuple[float, float]:
    """AUC (prob. de um degradado ter score maior que um não degradado) e Cliff's delta."""
    from scipy.stats import mannwhitneyu

    pos, neg = score[label == 1], score[label == 0]
    if len(pos) < 10 or len(neg) < 10:
        return np.nan, np.nan
    u = mannwhitneyu(pos, neg).statistic
    auc = u / (len(pos) * len(neg))
    return auc, 2 * auc - 1


def analyze() -> None:
    from scipy.stats import mannwhitneyu, spearmanr

    ref = _reference()
    scenes = sorted((OUT / "nisar").glob("*.csv"))
    nis = pd.concat([pd.read_csv(f).assign(date=f.stem) for f in scenes])
    agg = nis.groupby("id").agg(hv_db=("hv_db", "median"), hh_db=("hh_db", "median"),
                                hv_std=("hv_db", "std"), n_scenes=("hv_db", "count")).reset_index()
    agg["hvhh_db"] = agg.hv_db - agg.hh_db  # razão cross-pol: espalhamento volumétrico
    df = ref.merge(agg, on="id").dropna(subset=["hv_db"])
    df.to_csv(OUT / "tese_pontos.csv", index=False)

    lines = [f"# Teste da tese — núcleo {NUCLEO}", "",
             f"Pontos com referência e NISAR: {len(df)} · cenas NISAR: {len(scenes)} ({', '.join(f.stem for f in scenes)})", "",
             "## Referência (MODIS NDVI 2001–2024 corrigido por chuva CHIRPS, RESTREND)", "",
             df.ref_class.value_counts().to_frame("pontos").to_markdown(), ""]

    lines += ["## Sanidade: o NISAR enxerga vegetação?", "",
              "| Par | Spearman ρ | p |", "|---|---|---|"]
    for a, b in [("hv_db", "ndvi_mean"), ("hv_db", "ndvi_recent"), ("hvhh_db", "ndvi_recent"), ("hv_db", "resid_slope")]:
        rho, p = spearmanr(df[a], df[b], nan_policy="omit")
        lines.append(f"| {a} × {b} | {rho:.3f} | {p:.2g} |")
    lines.append("")

    label = (df.ref_class == "degradado").astype(int).to_numpy()
    lines += ["## Teste principal: degradado vs não degradado", "",
              "AUC > 0,5 = o sinal é MENOR nos degradados (usamos −sinal). Critério de apoio: AUC ≥ 0,70.", "",
              "| Sinal NISAR | Estrato | n degr. | n outros | mediana degr. | mediana outros | AUC | Cliff δ | p (Mann-Whitney) |",
              "|---|---|---|---|---|---|---|---|---|"]
    strata = [("todos", np.ones(len(df), bool))]
    if "lc" in df:
        for code, n in df.lc.value_counts().items():
            if n >= 60:
                strata.append((f"{IGBP.get(int(code), code)} ({int(code)})", (df.lc == code).to_numpy()))
    for sig in ["hv_db", "hvhh_db", "hh_db"]:
        for name, sel in strata:
            s, l = df[sig].to_numpy()[sel], label[sel]
            auc, delta = _auc(-s, l)
            if np.isnan(auc):
                continue
            p = mannwhitneyu(s[l == 1], s[l == 0]).pvalue
            lines.append(f"| {sig} | {name} | {(l == 1).sum()} | {(l == 0).sum()} | {np.median(s[l == 1]):.2f} | "
                         f"{np.median(s[l == 0]):.2f} | {auc:.3f} | {delta:.3f} | {p:.2g} |")
    lines.append("")

    # Controle: o NISAR acrescenta algo além do NDVI atual?
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import cross_val_predict
    X0 = df[["ndvi_recent"]].to_numpy()
    X1 = df[["ndvi_recent", "hv_db", "hvhh_db"]].to_numpy()
    if label.sum() >= 20:
        p0 = cross_val_predict(LogisticRegression(max_iter=1000), X0, label, cv=5, method="predict_proba")[:, 1]
        p1 = cross_val_predict(LogisticRegression(max_iter=1000), X1, label, cv=5, method="predict_proba")[:, 1]
        lines += ["## O NISAR acrescenta informação além do NDVI atual?", "",
                  f"- AUC só NDVI recente (validação cruzada 5×): {roc_auc_score(label, p0):.3f}",
                  f"- AUC NDVI recente + HV + HV/HH: {roc_auc_score(label, p1):.3f}", ""]

    report = "\n".join(lines)
    (OUT / "RESULTADO.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    {"points": points, "appeears-submit": appeears_submit, "appeears-fetch": appeears_fetch,
     "chirps": chirps, "nisar": nisar, "analyze": analyze}[step]()
