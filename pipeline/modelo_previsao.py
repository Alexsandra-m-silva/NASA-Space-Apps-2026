"""Quanto o NISAR ajuda a prever degradação? Ablação com séries temporais.

Alvos (o que acontece DEPOIS de 2014):
  T1 degradacao_recente: tendência de NDVI 2015–2024 descontada a chuva (RESTREND) < 0 com Mann-Kendall p < 0,10
  T2 degradacao_uso:     vegetação nativa em 2014 (MapBiomas) e desmatada 2015–2024 ou antrópica/solo exposto em 2024

Grupos de features:
  HIST   séries até 2014: NDVI anual (média, tendência, RESTREND, mínimo, CV, queda na seca de 2012),
         MapBiomas 2001 e 2014, desmatamento até 2014, vigor de pastagem 2014
  CLIMA  2001–2024: tendência de temperatura, chuva média 2015–2024 vs 2001–2014, aridez 2015–2024
  MODIS26 NDVI MODIS jun–out/2026 (mesma janela do NISAR)
  NISAR  HV, HH, HV/HH, textura, variação temporal, inclinação sazonal, sensibilidade do HV ao NDVI e à umidade do solo

Validação: XGBoost, GroupKFold por blocos espaciais de ~11 km, repetido com 3 sementes.
Uso: python -m pipeline.modelo_previsao
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
OUT = DATA_PROCESSED / "final_5"
CACHE = OUT / "series_pontos.csv"
B = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_"
YEARS = list(range(2001, 2025))
NATIVE = [3, 4, 5, 6, 11, 12, 13, 49, 50]


def sample_series(pts: pd.DataFrame) -> pd.DataFrame:
    import ee

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    modis = ee.ImageCollection("MODIS/061/MOD13Q1")
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD")
    era = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
    bands = []
    for y in YEARS:
        s, e = f"{y}-01-01", f"{y + 1}-01-01"
        bands.append(modis.filterDate(s, e).map(lambda i: i.select("NDVI").multiply(0.0001)
                                                .updateMask(i.select("SummaryQA").lte(1))).mean().rename(f"ndvi_{y}"))
        bands.append(chirps.filterDate(s, e).sum().rename(f"chuva_{y}"))
        bands.append(era.filterDate(s, e).select("temperature_2m").mean().subtract(273.15).rename(f"temp_{y}"))
        bands.append(era.filterDate(s, e).select("potential_evaporation_sum").sum().multiply(-1000).rename(f"etp_{y}"))
    lulc = ee.Image(B + "integration_v2")
    defo = ee.Image(B + "deforestation_secondary_vegetation_v2")
    loss = ee.ImageCollection([defo.select(f"classification_{y}").remap([4, 6], [1, 1], 0).multiply(y)
                               .toInt16().rename("v").selfMask() for y in YEARS]).min().unmask(0)
    vigor = ee.Image(B + "pasture_vigor_v3")
    bands += [lulc.select("classification_2001").rename("lc_2001"), lulc.select("classification_2014").rename("lc_2014"),
              lulc.select("classification_2024").rename("lc_2024"), loss.rename("ano_desmat"),
              vigor.select("classification_2014").unmask(0).rename("vigor_2014")]
    img = ee.Image.cat(bands)
    rows = []
    for k in range(0, len(pts), 500):
        chunk = pts.iloc[k:k + 500]
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"id": int(r.id)}) for r in chunk.itertuples()])
        res = img.reduceRegions(fc, ee.Reducer.first(), scale=250, tileScale=8).getInfo()["features"]
        rows += [f["properties"] for f in res]
        print("amostrados", k + len(chunk), flush=True)
    return pd.DataFrame(rows)


def _restrend(ndvi, rain, years):
    from scipy.stats import kendalltau, theilslopes
    ok = np.isfinite(ndvi) & np.isfinite(rain)
    if ok.sum() < max(6, len(years) - 3):
        return np.nan, np.nan
    b, a = np.polyfit(rain[ok], ndvi[ok], 1)
    resid = ndvi[ok] - (a + b * rain[ok])
    yrs = np.asarray(years)[ok]
    return theilslopes(resid, yrs)[0], kendalltau(yrs, resid).pvalue


def build(df: pd.DataFrame) -> pd.DataFrame:
    from scipy.stats import theilslopes

    h = [y for y in YEARS if y <= 2014]
    r = [y for y in YEARS if y >= 2015]
    nd = lambda ys: df[[f"ndvi_{y}" for y in ys]].to_numpy(float)
    ch = lambda ys: df[[f"chuva_{y}" for y in ys]].to_numpy(float)
    X = pd.DataFrame({"id": df.id})
    Nh, Ch = nd(h), ch(h)
    X["hist_ndvi_media"] = np.nanmean(Nh, 1)
    X["hist_ndvi_min"] = np.nanmin(Nh, 1)
    X["hist_ndvi_cv"] = np.nanstd(Nh, 1) / X.hist_ndvi_media
    X["hist_ndvi_tend"] = [theilslopes(row[np.isfinite(row)], np.asarray(h)[np.isfinite(row)])[0] if np.isfinite(row).sum() > 5 else np.nan for row in Nh]
    rr = [_restrend(a, b, h) for a, b in zip(Nh, Ch)]
    X["hist_restrend"] = [v[0] for v in rr]
    X["hist_queda_seca_2012"] = df.ndvi_2012 - np.nanmean(nd([2009, 2010, 2011]), 1)
    X["hist_lc_2001_nativa"] = df.lc_2001.isin(NATIVE).astype(int)
    X["hist_lc_2014_nativa"] = df.lc_2014.isin(NATIVE).astype(int)
    X["hist_lc_2014_pastagem"] = df.lc_2014.isin([15, 21]).astype(int)
    X["hist_desmat_ate_2014"] = ((df.ano_desmat > 0) & (df.ano_desmat <= 2014)).astype(int)
    X["hist_vigor_2014"] = df.vigor_2014
    T = df[[f"temp_{y}" for y in YEARS]].to_numpy(float)
    X["clima_temp_tend"] = [theilslopes(t, YEARS)[0] * 10 for t in T]
    X["clima_chuva_rec_vs_hist"] = np.nanmean(ch(r), 1) - np.nanmean(Ch, 1)
    X["clima_aridez_rec"] = np.nansum(ch(r), 1) / df[[f"etp_{y}" for y in r]].sum(1)
    X["clima_chuva_media"] = np.nanmean(ch(YEARS), 1)

    # alvos
    rec = [_restrend(a, b, r) for a, b in zip(nd(r), ch(r))]
    X["alvo_restrend_rec"] = [v[0] for v in rec]
    X["T1_degradacao_recente"] = [int(s < 0 and p < 0.10) if np.isfinite(s) else np.nan for s, p in rec]
    nat14 = df.lc_2014.isin(NATIVE)
    conv = (df.ano_desmat >= 2015) | df.lc_2024.isin([15, 21, 25, 24, 30, 75] + [39, 40, 41, 46, 47, 48, 62, 20])
    X["T2_degradacao_uso"] = np.where(nat14, conv.astype(int), np.nan)
    return X


def nisar_block():
    from pipeline.tese import _points, nisar_features

    nf = nisar_features("poligonos")
    # sensibilidade: inclinação da anomalia de HV contra anomalia de NDVI e umidade do solo
    v = pd.read_csv(OUT / "variacao_temporal_pontos.csv")
    for c in ("hv_db", "ndvi", "umidade_solo"):
        v[c] = v[c] - v.groupby("id")[c].transform("mean")

    def slope(g, x):
        g = g[["hv_db", x]].dropna()
        return np.polyfit(g[x], g.hv_db, 1)[0] if len(g) >= 4 and g[x].std() > 0 else np.nan
    sens = v.groupby("id").apply(lambda g: pd.Series({"nisar_sens_ndvi": slope(g, "ndvi"),
                                                       "nisar_sens_umidade": slope(g, "umidade_solo")}),
                                 include_groups=False).reset_index()
    pts = _points("poligonos")[["id", "lon", "lat", "regiao", "municipio"]]
    return pts.merge(nf, on="id").merge(sens, on="id", how="left")


def main() -> None:
    from sklearn.metrics import r2_score, roc_auc_score
    from sklearn.model_selection import GroupKFold
    from xgboost import XGBClassifier, XGBRegressor

    nb = nisar_block()
    if CACHE.exists():
        raw = pd.read_csv(CACHE)
    else:
        raw = sample_series(nb[["id", "lon", "lat"]])
        raw.to_csv(CACHE, index=False)
    X = build(raw)
    cov26 = pd.read_csv(OUT / "correlacoes_nisar_pontos.csv")[["id", "ndvi_jun_out_2026"]].rename(
        columns={"ndvi_jun_out_2026": "modis26_ndvi"})
    df = nb.merge(X, on="id").merge(cov26, on="id", how="left")
    df["bloco"] = np.floor(df.lon / 0.1).astype(int).astype(str) + "_" + np.floor(df.lat / 0.1).astype(int).astype(str)
    df.to_csv(OUT / "modelo_previsao_pontos.csv", index=False)

    HIST = [c for c in df if c.startswith("hist_")]
    CLIMA = [c for c in df if c.startswith("clima_")]
    NISAR = [c for c in df if c.startswith("nisar_") and c not in ("nisar_n_dates", "nisar_rvi")]
    M26 = ["modis26_ndvi"]
    sets = {
        "1. Histórico até 2014 + clima": HIST + CLIMA,
        "2. (1) + MODIS 2026": HIST + CLIMA + M26,
        "3. (1) + NISAR 2026": HIST + CLIMA + NISAR,
        "4. (1) + MODIS 2026 + NISAR 2026": HIST + CLIMA + M26 + NISAR,
        "5. Só NISAR 2026": NISAR,
        "6. Só MODIS 2026": M26,
    }

    def cv(cols, target, clf):
        d = df.dropna(subset=[target])
        Xm, y, g = d[cols].to_numpy(float), d[target].to_numpy(), d.bloco.to_numpy()
        scores = []
        for seed in (0, 1, 2):
            pred = np.full(len(d), np.nan)
            groups = pd.Series(g).map({b: i for i, b in enumerate(np.random.default_rng(seed).permutation(np.unique(g)))}).to_numpy()
            for tr, te in GroupKFold(n_splits=5).split(Xm, y, groups):
                kw = dict(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=5, random_state=seed)
                m = (XGBClassifier(eval_metric="logloss", **kw) if clf else XGBRegressor(**kw)).fit(Xm[tr], y[tr])
                pred[te] = m.predict_proba(Xm[te])[:, 1] if clf else m.predict(Xm[te])
            scores.append(roc_auc_score(y, pred) if clf else r2_score(y, pred))
        return np.mean(scores), np.std(scores), len(d), (d[target].mean() if clf else np.nan)

    L = ["# Quanto o NISAR ajuda a prever degradação?", "",
         f"Pontos: {len(df)} (14 municípios). XGBoost, validação por blocos espaciais (~11 km), média de 3 sementes.",
         "Features históricas só até 2014; alvo medido em 2015–2024; NISAR e MODIS 2026 = estado atual.", ""]
    targets = [("T1_degradacao_recente", True, "T1 — degradação recente da vegetação 2015–2024 (AUC)"),
               ("alvo_restrend_rec", False, "T1 contínuo — tendência RESTREND 2015–2024 (R²)"),
               ("T2_degradacao_uso", True, "T2 — Caatinga 2014 convertida/desmatada até 2024 (AUC)")]
    summary = {}
    for target, clf, title in targets:
        L += [f"## {title}", "", "| Conjunto | Métrica | ± | n | % positivos |", "|---|---|---|---|---|"]
        for name, cols in sets.items():
            m, s, n, pos = cv(cols, target, clf)
            summary[(target, name)] = m
            L.append(f"| {name} | {m:.3f} | {s:.3f} | {n} | {'' if np.isnan(pos) else f'{100*pos:.0f}%'} |")
        g_n = summary[(target, "3. (1) + NISAR 2026")] - summary[(target, "1. Histórico até 2014 + clima")]
        g_m = summary[(target, "2. (1) + MODIS 2026")] - summary[(target, "1. Histórico até 2014 + clima")]
        g_nm = summary[(target, "4. (1) + MODIS 2026 + NISAR 2026")] - summary[(target, "2. (1) + MODIS 2026")]
        L += ["", f"Ganho do NISAR sobre histórico+clima: **{g_n:+.3f}** · ganho do MODIS 2026: {g_m:+.3f} · "
                  f"ganho do NISAR além do MODIS 2026: **{g_nm:+.3f}**", ""]
    report = "\n".join(L)
    (OUT / "modelo_previsao.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
