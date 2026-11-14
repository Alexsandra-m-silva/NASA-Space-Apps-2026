"""Teste da tese: as features do NISAR explicam a desertificação observada pelo histórico?

Referência (independente do NISAR): RESTREND — tendência do NDVI MODIS 2001–2024 que a
chuva CHIRPS não explica. Ponto "degradado" = tendência negativa com Mann-Kendall p < 0,05.

Features NISAR (GCOV, dupla polarização, estação seca jun–out/2026, uma órbita por ponto):
mediana de HV, HH e HV/HH; variação temporal; inclinação sazonal; textura espacial; RVI dual.

Modelo: XGBoost só com features NISAR, validação cruzada espacial (deixa um município fora).
Comparação: o mesmo com NDVI atual (óptico) e com os dois juntos.

Uso (por área):
    python -m pipeline.tese AREA points|appeears-submit|appeears-fetch|chirps|nisar
    python -m pipeline.tese analyze            # junta todas as áreas prontas
Áreas: serido, sao_francisco
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

from pipeline.config import DATA_PROCESSED, DATA_RAW, ROOT

load_dotenv(ROOT / ".env")

AREAS = {
    "serido": {
        "municipios": [("Currais Novos", "RN"), ("Acari", "RN"), ("Parelhas", "RN"), ("Equador", "RN"),
                       ("Carnaúba dos Dantas", "RN"), ("Caicó", "RN"), ("Jardim do Seridó", "RN"), ("Cruzeta", "RN")],
        "points": 1000, "per_municipio": False,
    },
    "sao_francisco": {
        "municipios": [("Petrolina", "PE"), ("Juazeiro", "BA"), ("Casa Nova", "BA"), ("Floresta", "PE"),
                       ("Paulo Afonso", "BA"), ("Sobradinho", "BA")],
        "points": 150, "per_municipio": True,  # Casa Nova é enorme; sem isso dominaria a amostra
    },
    # Núcleos oficiais com estudos de campo publicados (ver docs/arquitetura_desertificacao.md)
    "comprovados": {
        "municipios": [("Gilbués", "PI"), ("Irauçuba", "CE"), ("Cabrobó", "PE"), ("Belém do São Francisco", "PE")],
        "points": 150, "per_municipio": True,
    },
}
SEED = 42
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api"
YEARS = range(2001, 2026)


def out_dir(area: str):
    d = DATA_PROCESSED / f"tese_{area}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- geometrias
def municipios_geojson(area: str) -> list[dict]:
    from pipeline.nucleos import IBGE_MALHA_UF, IBGE_MUN_UF, _get, _norm

    feats = []
    for nome, uf in AREAS[area]["municipios"]:
        muns = _get(IBGE_MUN_UF.format(uf=uf), f"municipios_{uf}.json")
        malha = _get(IBGE_MALHA_UF.format(uf=uf), f"malha_{uf}.geojson")
        code = {_norm(m["nome"]): str(m["id"]) for m in muns}[_norm(nome)]
        geom = {str(f["properties"]["codarea"]): f["geometry"] for f in malha["features"]}[code]
        feats.append({"type": "Feature", "properties": {"municipio": nome, "uf": uf, "ibge": code, "area": area},
                      "geometry": geom})
    return feats


def points(area: str) -> None:
    from shapely.geometry import Point, shape

    cfg = AREAS[area]
    feats = municipios_geojson(area)
    (out_dir(area) / "municipios.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    rng = np.random.default_rng(SEED)
    polys = [(f["properties"]["municipio"], shape(f["geometry"])) for f in feats]

    def sample(poly, n):
        minx, miny, maxx, maxy = poly.bounds
        got = []
        while len(got) < n:
            x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
            if poly.contains(Point(x, y)):
                got.append((round(x, 6), round(y, 6)))
        return got

    rows = []
    if cfg["per_municipio"]:
        for nome, poly in polys:
            rows += [(nome, x, y) for x, y in sample(poly, cfg["points"])]
    else:
        from shapely.ops import unary_union
        for x, y in sample(unary_union([p for _, p in polys]), cfg["points"]):
            nome = next(n for n, p in polys if p.contains(Point(x, y)))
            rows.append((nome, x, y))
    df = pd.DataFrame(rows, columns=["municipio", "lon", "lat"])
    df.insert(0, "id", range(len(df)))
    df.to_csv(out_dir(area) / "points.csv", index=False)
    print(df.municipio.value_counts().to_string())


def _points(area: str) -> pd.DataFrame:
    df = pd.read_csv(out_dir(area) / "points.csv")
    if "municipio" not in df:  # pontos do Seridó gerados pela versão anterior
        from shapely.geometry import Point, shape
        feats = municipios_geojson(area)
        polys = [(f["properties"]["municipio"], shape(f["geometry"])) for f in feats]
        df["municipio"] = [next((n for n, p in polys if p.contains(Point(x, y))), None) for x, y in zip(df.lon, df.lat)]
        df.to_csv(out_dir(area) / "points.csv", index=False)
    return df


# ---------------------------------------------------------------- AppEEARS (MODIS)
def _token() -> str:
    r = requests.post(f"{APPEEARS}/login", auth=(os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"]), timeout=60)
    r.raise_for_status()
    return r.json()["token"]


def appeears_submit(area: str) -> None:
    pts = _points(area)
    task = {
        "task_type": "point",
        "task_name": f"tese_{area}_ndvi",
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
    print(r.status_code, r.text[:300])
    r.raise_for_status()
    (out_dir(area) / "appeears_task.json").write_text(r.text, encoding="utf-8")


def appeears_fetch(area: str) -> None:
    task_id = json.loads((out_dir(area) / "appeears_task.json").read_text())["task_id"]
    while True:
        headers = {"Authorization": f"Bearer {_token()}"}
        st = requests.get(f"{APPEEARS}/task/{task_id}", headers=headers, timeout=60).json()
        print(time.strftime("%H:%M:%S"), area, st.get("status"), flush=True)
        if st.get("status") == "done":
            break
        if st.get("status") == "error":
            raise SystemExit(st)
        time.sleep(120)
    bundle = requests.get(f"{APPEEARS}/bundle/{task_id}", headers=headers, timeout=60).json()
    for f in bundle["files"]:
        if f["file_name"].endswith(".csv"):
            data = requests.get(f"{APPEEARS}/bundle/{task_id}/{f['file_id']}", headers=headers, timeout=600)
            (out_dir(area) / f["file_name"].split("/")[-1]).write_bytes(data.content)
            print("baixado", f["file_name"], flush=True)


# ---------------------------------------------------------------- CHIRPS
def chirps(area: str) -> None:
    import rasterio

    pts = _points(area)
    coords = list(zip(pts.lon, pts.lat))
    cols = {}
    for y in YEARS:
        url = f"/vsicurl/https://data.chc.ucsb.edu/products/CHIRPS/v2.0/global_annual/tifs/chirps-v2.0.{y}.tif"
        for attempt in range(3):
            try:
                with rasterio.open(url) as src:
                    cols[y] = [v[0] for v in src.sample(coords)]
                break
            except Exception as e:
                if attempt == 2:
                    print(y, "indisponível:", type(e).__name__)
                time.sleep(5)
    df = pd.DataFrame(cols, index=pts.id).astype(float)
    df[df < 0] = np.nan
    df.to_csv(out_dir(area) / "chirps_annual.csv")
    print("anos:", list(df.columns))


# ---------------------------------------------------------------- NISAR
NISAR_PRODUCT = "NISAR_L2_GCOV_PROVISIONAL_V1"
NISAR_GROUP = "science/LSAR/GCOV/grids/frequencyA"
HALF = 6  # 13 x 13 px de 20 m ~ 250 m (pixel MODIS)


def _track_frame(ur: str) -> str:
    p = ur.split("_")  # NISAR_L2_PR_GCOV_cycle_track_dir_frame_mode_pol_...
    return f"{p[5]}_{p[6]}_{p[7]}"


def _polygon(g):
    from shapely.geometry import Polygon
    gp = g["umm"]["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]["GPolygons"][0]
    return Polygon([(p["Longitude"], p["Latitude"]) for p in gp["Boundary"]["Points"]])


def nisar(area: str) -> None:
    import earthaccess
    import h5py
    from pyproj import Transformer
    from shapely.geometry import Point

    earthaccess.login(strategy="environment")
    pts = _points(area)
    bbox = (pts.lon.min() - .02, pts.lat.min() - .02, pts.lon.max() + .02, pts.lat.max() + .02)
    grans = [g for g in earthaccess.search_data(short_name=NISAR_PRODUCT, bounding_box=bbox, count=2000)
             if "_DHDH_" in g["umm"]["GranuleUR"]]

    # Para cada ponto: a órbita/frame com mais datas que o cobre (mesma geometria no tempo).
    by_tf: dict[str, list] = {}
    for g in grans:
        by_tf.setdefault(_track_frame(g["umm"]["GranuleUR"]), []).append(g)
    tf_poly = {tf: _polygon(gs[0]) for tf, gs in by_tf.items()}
    ranked = sorted(by_tf, key=lambda tf: -len(by_tf[tf]))
    assign = {}
    for r in pts.itertuples():
        p = Point(r.lon, r.lat)
        assign[r.id] = next((tf for tf in ranked if tf_poly[tf].buffer(-0.01).contains(p)), None)
    pts["track_frame"] = pts.id.map(assign)
    pts.to_csv(out_dir(area) / "points_nisar.csv", index=False)
    print(pts.track_frame.value_counts(dropna=False).to_string())

    cache = out_dir(area) / "nisar_v2"
    cache.mkdir(exist_ok=True)
    for tf in pts.track_frame.dropna().unique():
        sel = pts[pts.track_frame == tf]
        for g in by_tf[tf]:
            ur = g["umm"]["GranuleUR"]
            date = ur.split("_")[11][:8]
            out = cache / f"{tf}_{date}.csv"
            if out.exists():
                continue
            try:
                f = earthaccess.open([g])[0]
                with h5py.File(f, "r") as h:
                    grp = h[NISAR_GROUP]
                    x, y = grp["xCoordinates"][()], grp["yCoordinates"][()]
                    tr = Transformer.from_crs(4326, int(grp["projection"].attrs["epsg_code"]), always_xy=True)
                    px, py = tr.transform(sel.lon.values, sel.lat.values)
                    col = np.round((px - x[0]) / (x[1] - x[0])).astype(int)
                    row = np.round((py - y[0]) / (y[1] - y[0])).astype(int)
                    inside = (col >= HALF) & (col < len(x) - HALF) & (row >= HALF) & (row < len(y) - HALF)
                    if not inside.any():
                        continue
                    r0, r1 = row[inside].min() - HALF, row[inside].max() + HALF + 1
                    c0, c1 = col[inside].min() - HALF, col[inside].max() + HALF + 1
                    hv = grp["HVHV"][r0:r1, c0:c1]
                    hh = grp["HHHH"][r0:r1, c0:c1]
                    mask = grp["mask"][r0:r1, c0:c1]
            except Exception as e:
                print(ur, "falhou:", type(e).__name__, e, flush=True)
                continue
            valid = (mask > 0) & (mask < 255) & np.isfinite(hv) & (hv > 0) & np.isfinite(hh) & (hh > 0)
            rows = []
            for pid, ok, rr, cc in zip(sel.id, inside, row - r0, col - c0):
                if not ok:
                    continue
                sl = np.s_[rr - HALF: rr + HALF + 1, cc - HALF: cc + HALF + 1]
                v = valid[sl]
                if v.sum() < 0.5 * v.size:
                    continue
                hvw, hhw = hv[sl][v], hh[sl][v]
                rows.append({"id": pid, "date": date, "hv_lin": hvw.mean(), "hh_lin": hhw.mean(),
                             "hv_tex": np.std(10 * np.log10(hvw)), "hh_tex": np.std(10 * np.log10(hhw)),
                             "n_valid": int(v.sum())})
            pd.DataFrame(rows).to_csv(out, index=False)
            print(area, tf, date, "pontos:", len(rows), flush=True)


def nisar_features(area: str) -> pd.DataFrame:
    files = sorted((out_dir(area) / "nisar_v2").glob("*.csv"))
    d = pd.concat([pd.read_csv(f) for f in files if f.stat().st_size > 5])
    d["hv_db"], d["hh_db"] = 10 * np.log10(d.hv_lin), 10 * np.log10(d.hh_lin)
    d["t"] = (pd.to_datetime(d.date.astype(str)) - pd.Timestamp("2026-06-01")).dt.days / 30.0

    def per_point(g):
        slope_hv = np.polyfit(g.t, g.hv_db, 1)[0] if g.t.nunique() >= 4 else np.nan
        slope_hh = np.polyfit(g.t, g.hh_db, 1)[0] if g.t.nunique() >= 4 else np.nan
        hv, hh = g.hv_lin.median(), g.hh_lin.median()
        return pd.Series({
            "nisar_hv_db": 10 * np.log10(hv), "nisar_hh_db": 10 * np.log10(hh),
            "nisar_hvhh_db": 10 * np.log10(hv / hh),
            "nisar_rvi": 4 * hv / (hh + hv),  # índice de vegetação radar (dupla pol.)
            "nisar_hv_std_t": g.hv_db.std(), "nisar_hh_std_t": g.hh_db.std(),
            "nisar_hv_slope": slope_hv, "nisar_hh_slope": slope_hh,
            "nisar_hv_tex": g.hv_tex.median(), "nisar_hh_tex": g.hh_tex.median(),
            "nisar_n_dates": g.date.nunique(),
        })
    return d.groupby("id").apply(per_point, include_groups=False).reset_index()


# ---------------------------------------------------------------- referência
def reference(area: str) -> pd.DataFrame:
    from scipy.stats import kendalltau, theilslopes

    od = out_dir(area)
    files = sorted(od.glob("*MOD13Q1*results.csv"))
    if not files:
        raise FileNotFoundError(f"{area}: falta o resultado do AppEEARS")
    m = pd.read_csv(files[0])
    ndvi_col = next(c for c in m.columns if c.endswith("_250m_16_days_NDVI"))
    rel_col = next(c for c in m.columns if c.endswith("_pixel_reliability"))
    m = m[m[rel_col].isin([0, 1])].copy()
    m["year"] = pd.to_datetime(m["Date"]).dt.year
    ndvi = m.groupby(["ID", "year"])[ndvi_col].mean().unstack()
    rain = pd.read_csv(od / "chirps_annual.csv", index_col=0)
    rain.columns = rain.columns.astype(int)
    years = [y for y in ndvi.columns if y in rain.columns]
    rows = []
    for pid in ndvi.index:
        n, r = ndvi.loc[pid, years].to_numpy(float), rain.loc[pid, years].to_numpy(float)
        ok = np.isfinite(n) & np.isfinite(r)
        if ok.sum() < 15:
            continue
        yrs = np.asarray(years)[ok]
        b, a = np.polyfit(r[ok], n[ok], 1)
        resid = n[ok] - (a + b * r[ok])
        tau, p = kendalltau(yrs, resid)
        rows.append({"id": pid, "resid_slope": theilslopes(resid, yrs)[0], "resid_p": p,
                     "ndvi_mean": n[ok].mean(), "ndvi_recent": n[ok][-3:].mean(),
                     "ndvi_raw_slope": theilslopes(n[ok], yrs)[0]})
    ref = pd.DataFrame(rows)
    ref["ref_class"] = np.select([(ref.resid_slope < 0) & (ref.resid_p < .05), (ref.resid_slope > 0) & (ref.resid_p < .05)],
                                 ["degradado", "melhora"], "estavel")
    lc_files = sorted(od.glob("*MCD12Q1*results.csv"))
    if lc_files:
        lc = pd.read_csv(lc_files[0])
        lc_col = next(c for c in lc.columns if c.endswith("LC_Type1"))
        lc["year"] = pd.to_datetime(lc["Date"]).dt.year
        ref["lc"] = ref.id.map(lc.sort_values("year").groupby("ID")[lc_col].last())
    return ref


# ---------------------------------------------------------------- análise
IGBP = {7: "Arbustiva aberta", 8: "Savana arborizada", 9: "Savana", 10: "Campo", 12: "Agricultura",
        13: "Urbano", 14: "Mosaico agric./natural", 16: "Solo exposto", 17: "Água"}


def analyze() -> None:
    from scipy.stats import mannwhitneyu, spearmanr
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import r2_score, roc_auc_score
    from sklearn.model_selection import GroupKFold
    from xgboost import XGBClassifier, XGBRegressor

    frames, skipped = [], []
    for area in AREAS:
        try:
            ref = reference(area)
            nf = nisar_features(area)
        except (FileNotFoundError, ValueError) as e:
            skipped.append(f"{area}: {e}")
            continue
        pts = _points(area)[["id", "municipio", "lon", "lat"]]
        frames.append(pts.merge(ref, on="id").merge(nf, on="id").assign(area=area))
    if not frames:
        raise SystemExit("Nenhuma área pronta: " + "; ".join(skipped))
    df = pd.concat(frames, ignore_index=True)
    n_all = len(df)
    df = df[~df.lc.isin([13, 17])]  # urbano e água não entram
    df = df.dropna(subset=["nisar_hv_db"])
    df["y"] = (df.ref_class == "degradado").astype(int)
    df["group"] = df.area + ":" + df.municipio.astype(str)
    od = DATA_PROCESSED / "tese_resultado"
    od.mkdir(exist_ok=True)
    df.to_csv(od / "pontos.csv", index=False)

    feats = [c for c in df.columns if c.startswith("nisar_") and c != "nisar_n_dates"]
    L = [f"# As features do NISAR explicam a desertificação?", "",
         f"Áreas: {', '.join(df.area.unique())}" + (f" · pendentes: {'; '.join(skipped)}" if skipped else ""),
         f"Pontos: {len(df)} (de {n_all}; fora urbano/água e sem NISAR) · municípios: {df.group.nunique()}", "",
         "## Referência independente (MODIS NDVI 2001–2024 corrigido por chuva CHIRPS)", "",
         pd.crosstab(df.group, df.ref_class, margins=True).to_markdown(), ""]

    # 1) cada feature sozinha
    L += ["## 1. Cada feature NISAR, degradado vs não degradado", "",
          "AUC 0,5 = sem informação. AUC < 0,5 = feature MENOR nos degradados (reportamos max(AUC, 1−AUC) e a direção).", "",
          "| Feature | mediana degr. | mediana outros | AUC | direção | p (Mann-Whitney) | ρ Spearman c/ tendência NDVI |",
          "|---|---|---|---|---|---|---|"]
    for f in feats:
        s = df[f].to_numpy(); y = df.y.to_numpy(); ok = np.isfinite(s)
        if (y[ok] == 1).sum() < 10:
            continue
        auc = roc_auc_score(y[ok], s[ok])
        p = mannwhitneyu(s[ok][y[ok] == 1], s[ok][y[ok] == 0]).pvalue
        rho = spearmanr(s[ok], df.resid_slope.to_numpy()[ok]).statistic
        L.append(f"| {f} | {np.median(s[ok][y[ok]==1]):.3f} | {np.median(s[ok][y[ok]==0]):.3f} | "
                 f"{max(auc, 1-auc):.3f} | {'maior' if auc > .5 else 'menor'} nos degradados | {p:.2g} | {rho:.3f} |")
    L.append("")

    # 2) modelo multivariado com validação espacial
    def cv_auc(cols, clf=True):
        X, y, g = df[cols].to_numpy(float), df.y.to_numpy(), df.group.to_numpy()
        pred = np.full(len(df), np.nan)
        for tr, te in GroupKFold(n_splits=min(5, df.group.nunique())).split(X, y, g):
            mdl = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=.05, subsample=.8,
                                colsample_bytree=.8, min_child_weight=5, eval_metric="logloss", random_state=SEED)
            mdl.fit(X[tr], y[tr])
            pred[te] = mdl.predict_proba(X[te])[:, 1]
        return roc_auc_score(y, pred)

    def cv_r2(cols):
        X, t, g = df[cols].to_numpy(float), df.resid_slope.to_numpy(), df.group.to_numpy()
        pred = np.full(len(df), np.nan)
        for tr, te in GroupKFold(n_splits=min(5, df.group.nunique())).split(X, t, g):
            mdl = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=.05, subsample=.8,
                               colsample_bytree=.8, min_child_weight=5, random_state=SEED)
            mdl.fit(X[tr], t[tr])
            pred[te] = mdl.predict(X[te])
        return r2_score(t, pred)

    L += ["## 2. Modelo XGBoost, validação cruzada espacial (municípios inteiros fora do treino)", "",
          "| Conjunto de variáveis | AUC (degradado sim/não) | R² (tendência contínua) |", "|---|---|---|"]
    sets = {"Só NISAR": feats, "Só NDVI atual (óptico, referência)": ["ndvi_recent"],
            "NDVI atual + NISAR": ["ndvi_recent"] + feats}
    res = {}
    for name, cols in sets.items():
        res[name] = (cv_auc(cols), cv_r2(cols))
        L.append(f"| {name} | {res[name][0]:.3f} | {res[name][1]:.3f} |")
    L.append("")

    # 3) importância das features NISAR
    mdl = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=.05, subsample=.8, colsample_bytree=.8,
                        min_child_weight=5, eval_metric="logloss", random_state=SEED).fit(df[feats], df.y)
    imp = permutation_importance(mdl, df[feats], df.y, scoring="roc_auc", n_repeats=20, random_state=SEED)
    order = np.argsort(-imp.importances_mean)
    L += ["## 3. Quais variáveis NISAR pesam (importância por permutação, queda de AUC)", "",
          "| Feature | queda de AUC | ± |", "|---|---|---|"]
    L += [f"| {feats[i]} | {imp.importances_mean[i]:.4f} | {imp.importances_std[i]:.4f} |" for i in order]
    L.append("")

    auc_n = res["Só NISAR"][0]
    verdict = ("APOIA a tese (AUC ≥ 0,70 com municípios fora do treino)" if auc_n >= .70 else
               "APOIO PARCIAL (sinal acima do acaso, abaixo de 0,70)" if auc_n >= .60 else
               "NÃO APOIA a tese com estes dados")
    L += ["## Veredito", "", f"Só NISAR: AUC = {auc_n:.3f} → **{verdict}**.", "",
          "Limites: NISAR provisório e só estação seca de 2026; referência é tendência de NDVI (não medida de campo); "
          "lista de municípios do Seridó não verificada na fonte primária."]
    report = "\n".join(L)
    (od / "RESULTADO.md").write_text(report, encoding="utf-8")
    print(report)


def analyze_poligonos() -> None:
    """Polígonos MODIS (degradado / controle / melhora) x NISAR com gradient boosting.

    Pergunta: o NISAR acusa degradação nos polígonos degradados (sensibilidade) e
    deixa de acusar nos polígonos de controle e de melhora (especificidade)?
    Validação cruzada por blocos espaciais de ~11 km: pixels vizinhos nunca ficam
    um no treino e outro no teste.
    """
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve
    from sklearn.model_selection import GroupKFold
    from xgboost import XGBClassifier

    area = "poligonos"
    pts = _points(area)
    df = pts.merge(nisar_features(area), on="id").dropna(subset=["nisar_hv_db"])
    df["bloco"] = (np.floor(df.lon / 0.1)).astype(int).astype(str) + "_" + (np.floor(df.lat / 0.1)).astype(int).astype(str)
    feats = [c for c in df.columns if c.startswith("nisar_") and c != "nisar_n_dates"]
    train = df[df.classe.isin(["degradado", "controle_estavel"])].reset_index(drop=True)
    y = (train.classe == "degradado").astype(int).to_numpy()
    X, groups = train[feats].to_numpy(float), train.bloco.to_numpy()

    def model():
        return XGBClassifier(n_estimators=400, max_depth=3, learning_rate=.05, subsample=.8, colsample_bytree=.8,
                             min_child_weight=5, eval_metric="logloss", random_state=SEED)

    prob = np.full(len(train), np.nan)
    thr_folds = []
    melhora = df[df.classe == "melhora"]
    prob_melhora = []
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
        m = model().fit(X[tr], y[tr])
        p_tr = m.predict_proba(X[tr])[:, 1]
        fpr, tpr, thr = roc_curve(y[tr], p_tr)
        thr_folds.append(thr[np.argmax(tpr - fpr)])  # limiar escolhido só no treino (Youden)
        prob[te] = m.predict_proba(X[te])[:, 1]
        if len(melhora):
            prob_melhora.append(m.predict_proba(melhora[feats].to_numpy(float))[:, 1])
    thr = float(np.median(thr_folds))
    pred = (prob >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    auc = roc_auc_score(y, prob)
    sens, spec = tp / (tp + fn), tn / (tn + fp)
    fp_melhora = float((np.mean(prob_melhora, axis=0) >= thr).mean()) if prob_melhora else np.nan

    train["prob_nisar"], train["pred_nisar"] = prob, pred
    od = DATA_PROCESSED / "tese_resultado"
    od.mkdir(exist_ok=True)
    train.to_csv(od / "poligonos_pontos.csv", index=False)

    L = ["# Polígonos MODIS validados pelo NISAR (gradient boosting)", "",
         f"Pontos: {len(train)} (degradado {int(y.sum())}, controle {int((1-y).sum())}) + melhora {len(melhora)} · "
         f"blocos espaciais: {train.bloco.nunique()}", "",
         "## Resultado (validação cruzada por blocos espaciais)", "",
         f"- AUC: **{auc:.3f}**",
         f"- Limiar (escolhido só no treino): {thr:.3f}",
         f"- Sensibilidade (degradado → NISAR acusa): **{sens:.1%}**",
         f"- Especificidade (controle → NISAR NÃO acusa): **{spec:.1%}**",
         f"- Falso alarme em polígonos de MELHORA (ex.: irrigação nova): **{fp_melhora:.1%}**", "",
         "| | NISAR: degradado | NISAR: não degradado |", "|---|---|---|",
         f"| MODIS: degradado | {tp} | {fn} |", f"| MODIS: controle | {fp} | {tn} |", ""]

    L += ["## Por região", "", "| Região | n | AUC | sensibilidade | especificidade |", "|---|---|---|---|---|"]
    for reg, g in train.groupby("regiao"):
        yy, pp = (g.classe == "degradado").astype(int), g.prob_nisar
        if yy.nunique() < 2:
            continue
        s = ((pp >= thr) & (yy == 1)).sum() / max((yy == 1).sum(), 1)
        e = ((pp < thr) & (yy == 0)).sum() / max((yy == 0).sum(), 1)
        L.append(f"| {reg} | {len(g)} | {roc_auc_score(yy, pp):.3f} | {s:.1%} | {e:.1%} |")
    L.append("")

    full = model().fit(X, y)
    imp = permutation_importance(full, X, y, scoring="roc_auc", n_repeats=20, random_state=SEED)
    L += ["## Variáveis NISAR que mais pesam", "", "| Feature | queda de AUC |", "|---|---|"]
    L += [f"| {feats[i]} | {imp.importances_mean[i]:.4f} |" for i in np.argsort(-imp.importances_mean)]
    L += ["", "## Veredito", ""]
    ok = auc >= .70 and spec >= .70
    L.append(("**O NISAR corrobora o mapa MODIS**: separa degradado de controle com AUC ≥ 0,70 e especificidade ≥ 70%."
              if ok else "**O NISAR não corrobora o mapa MODIS com força suficiente** (critério: AUC ≥ 0,70 e especificidade ≥ 70%)."))
    report = "\n".join(L)
    (od / "RESULTADO_POLIGONOS.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    if sys.argv[1] == "analyze":
        analyze()
    elif sys.argv[1] == "analyze-poligonos":
        analyze_poligonos()
    else:
        area, step = sys.argv[1], sys.argv[2]
        {"points": points, "appeears-submit": appeears_submit, "appeears-fetch": appeears_fetch,
         "chirps": chirps, "nisar": nisar}[step](area)
