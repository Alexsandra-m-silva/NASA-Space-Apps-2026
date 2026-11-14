"""As variações do NISAR em jun–out/2026 aparecem nos outros dados no mesmo período?

Para cada ponto e cada data de passagem NISAR, amostra no GEE:
- NDVI MODIS (MOD13Q1 + MYD13Q1, composto de 16 dias que contém a data)
- umidade do solo 0–7 cm ERA5-Land (média dos 3 dias anteriores à passagem)
- chuva CHIRPS diária acumulada nos 12 dias anteriores (um ciclo NISAR)
- temperatura máxima ERA5-Land (média dos 3 dias anteriores)

Análise "dentro do ponto": cada variável vira anomalia em relação à média do próprio ponto
(remove diferenças de lugar); correlaciona as anomalias do NISAR com as dos outros dados.

Uso: python -m pipeline.variacao_temporal
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
OUT = DATA_PROCESSED / "final_5"
NIS_DIR = DATA_PROCESSED / "tese_poligonos" / "nisar_v2"


def main() -> None:
    import ee
    from scipy.stats import spearmanr

    from pipeline.tese import _points

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    pts = _points("poligonos")
    nis = pd.concat([pd.read_csv(f) for f in NIS_DIR.glob("*.csv") if f.stat().st_size > 5])
    nis["hv_db"], nis["hh_db"] = 10 * np.log10(nis.hv_lin), 10 * np.log10(nis.hh_lin)
    nis["date"] = pd.to_datetime(nis.date.astype(str))
    nis = nis.merge(pts[["id", "lon", "lat", "classe", "regiao"]], on="id")

    modis = ee.ImageCollection("MODIS/061/MOD13Q1").merge(ee.ImageCollection("MODIS/061/MYD13Q1"))
    era_d = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")

    rows = []
    dates = sorted(nis.date.unique())
    for d in dates:
        d = pd.Timestamp(d)
        sel = nis[nis.date == d]
        ds = d.strftime("%Y-%m-%d")
        ndvi = (modis.filterDate((d - pd.Timedelta(days=15)).strftime("%Y-%m-%d"), (d + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
                .map(lambda i: i.select("NDVI").multiply(0.0001).updateMask(i.select("SummaryQA").lte(1))).mean().rename("ndvi"))
        e3 = era_d.filterDate((d - pd.Timedelta(days=3)).strftime("%Y-%m-%d"), ds)
        sm = ee.Image(ee.Algorithms.If(e3.size().gt(0), e3.select("volumetric_soil_water_layer_1").mean(),
                                       ee.Image.constant(-999))).rename("umidade_solo")
        tmax = ee.Image(ee.Algorithms.If(e3.size().gt(0), e3.select("temperature_2m_max").mean().subtract(273.15),
                                         ee.Image.constant(-999))).rename("tmax")
        c12 = chirps.filterDate((d - pd.Timedelta(days=12)).strftime("%Y-%m-%d"), ds)
        rain = ee.Image(ee.Algorithms.If(c12.size().gt(0), c12.sum(), ee.Image.constant(-999))).rename("chuva_12d")
        img = ee.Image.cat([ndvi, sm, tmax, rain])
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"id": int(r.id)}) for r in sel.itertuples()])
        res = img.reduceRegions(fc, ee.Reducer.first(), scale=250, tileScale=4).getInfo()["features"]
        for f in res:
            rows.append({"id": f["properties"]["id"], "date": d} |
                        {k: f["properties"].get(k) for k in ("ndvi", "umidade_solo", "tmax", "chuva_12d")})
        print(ds, len(sel), flush=True)

    cov = pd.DataFrame(rows).replace(-999, np.nan)
    df = nis.merge(cov, on=["id", "date"])
    df.to_csv(OUT / "variacao_temporal_pontos.csv", index=False)
    other = [c for c in ("ndvi", "umidade_solo", "tmax", "chuva_12d") if df[c].notna().sum() > 100]
    nisv = ["hv_db", "hh_db"]

    # anomalias dentro do ponto
    an = df.copy()
    for c in nisv + other:
        an[c] = an[c] - an.groupby("id")[c].transform("mean")
    an = an[an.groupby("id").date.transform("nunique") >= 4]

    L = ["# Variações do NISAR em jun–out/2026 × outros dados no mesmo período", "",
         f"Pontos com ≥ 4 datas: {an.id.nunique()} · observações: {len(an)} · datas NISAR: {len(dates)} "
         f"({pd.Timestamp(dates[0]).date()} a {pd.Timestamp(dates[-1]).date()})", "",
         "Anomalias dentro do ponto (cada valor menos a média do próprio ponto). ρ de Spearman.", "",
         "| NISAR × | " + " | ".join(other) + " |", "|---|" + "---|" * len(other)]
    for n in nisv:
        cells = []
        for o in other:
            ok = an[[n, o]].dropna()
            r = spearmanr(ok[n], ok[o])
            cells.append(f"{r.statistic:+.2f}" + ("" if r.pvalue < 0.05 else " (ns)") + f" (n={len(ok)})")
        L.append(f"| {n} | " + " | ".join(cells) + " |")

    # por classe de referência
    L += ["", "## HV × NDVI por classe (anomalias dentro do ponto)", "", "| Classe | n | ρ HV×NDVI | ρ HV×umidade do solo |", "|---|---|---|---|"]
    for cls, g in an.groupby("classe"):
        r1 = spearmanr(g.hv_db, g.ndvi, nan_policy="omit").statistic
        r2 = spearmanr(g.hv_db, g.umidade_solo, nan_policy="omit").statistic if "umidade_solo" in other else np.nan
        L.append(f"| {cls} | {len(g)} | {r1:+.2f} | {r2:+.2f} |")

    # trajetória média regional por data
    traj = df.groupby(["regiao", df.date.dt.strftime("%Y-%m-%d")])[nisv + other].mean().round(3)
    traj.to_csv(OUT / "variacao_temporal_trajetoria.csv")
    L += ["", "## Trajetória média por data (região)", "", traj.to_markdown(), ""]
    report = "\n".join(L)
    (OUT / "variacao_temporal.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
