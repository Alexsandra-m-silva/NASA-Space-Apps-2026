"""Correlação dos indicadores NISAR (jun–out/2026) com MapBiomas e outras camadas.

Pontos: os já usados na validação por polígonos (degradado, controle e melhora; 14 municípios).
Indicadores NISAR: HV, HH, HV/HH, RVI, variação temporal, inclinação sazonal, textura.

Camadas comparadas (amostradas no GEE no ponto):
- MapBiomas Col. 10: classe de uso 2024, vigor de pastagem 2024, desmatamento 2001–2024 (e ano),
  idade da vegetação secundária, frequência de fogo 2001–2024, fração de areia do solo.
- MODIS: NDVI médio jun–out/2026 (mesma janela do NISAR) e tendência 2001–2024 (RESTREND).
- CHIRPS: chuva jan–mai/2026 (estação chuvosa anterior) e jun–out/2026.
- ERA5-Land: temperatura média jun–out/2026.

Saída: data/processed/final_5/correlacoes_nisar.md (+ CSVs)
Uso: python -m pipeline.correlacoes_nisar
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
OUT = DATA_PROCESSED / "final_5"
B = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_"
SAND = "projects/mapbiomas-public/assets/brazil/soil/collection3/mapbiomas_brazil_collection3_soil_sand_fraction_v1"
FIRE = "projects/mapbiomas-public/assets/brazil/fire/collection4/mapbiomas_fire_collection4_annual_burned_v1"
CLASSES = {3: "Floresta", 4: "Savana (Caatinga)", 12: "Campo", 15: "Pastagem", 21: "Mosaico de usos",
           25: "Solo exposto / não vegetado", 29: "Afloramento rochoso", 41: "Lavoura temporária",
           48: "Lavoura perene", 20: "Cana", 24: "Urbano", 33: "Água", 75: "Usina solar"}
NISAR_LABELS = {"nisar_hv_db": "HV (dB)", "nisar_hh_db": "HH (dB)", "nisar_hvhh_db": "HV/HH (dB)",
                "nisar_rvi": "RVI", "nisar_hv_std_t": "HV variação temporal", "nisar_hh_std_t": "HH variação temporal",
                "nisar_hv_slope": "HV inclinação sazonal", "nisar_hh_slope": "HH inclinação sazonal",
                "nisar_hv_tex": "HV textura", "nisar_hh_tex": "HH textura"}


def covariates():
    import ee

    lulc = ee.Image(B + "integration_v2")
    defo = ee.Image(B + "deforestation_secondary_vegetation_v2")
    loss_year = ee.ImageCollection([defo.select(f"classification_{y}").remap([4, 6], [1, 1], 0)
                                    .multiply(y).toInt16().rename("v").selfMask() for y in range(2001, 2025)]).max()
    secveg = defo.select("classification_2024").eq(3)
    vigor = ee.Image(B + "pasture_vigor_v3").select("classification_2024")
    fire = ee.Image(FIRE)
    fire_freq = ee.ImageCollection([fire.select(f"burned_area_{y}").gt(0).unmask(0).toUint8().rename("v")
                                    for y in range(2001, 2025)]).sum()
    sand = ee.ImageCollection(SAND).mosaic().select([0])
    ndvi26 = (ee.ImageCollection("MODIS/061/MOD13Q1").filterDate("2026-06-01", "2026-11-01")
              .map(lambda i: i.select("NDVI").multiply(0.0001).updateMask(i.select("SummaryQA").lte(1))).mean())
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD")
    rain_wet = chirps.filterDate("2026-01-01", "2026-06-01").sum()
    rain_dry = chirps.filterDate("2026-06-01", "2026-11-01").sum()
    era = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR").filterDate("2026-06-01", "2026-11-01")
    temp = ee.Image(ee.Algorithms.If(era.size().gt(0), era.select("temperature_2m").mean().subtract(273.15),
                                     ee.Image.constant(-999))).rename("temp_jun_out_2026")
    return ee.Image.cat([
        lulc.select("classification_2024").rename("mapbiomas_2024"),
        lulc.select("classification_2001").rename("mapbiomas_2001"),
        vigor.unmask(0).rename("vigor_pastagem_2024"),
        loss_year.unmask(0).rename("ano_desmatamento"),
        secveg.rename("veg_secundaria_2024"),
        fire_freq.rename("anos_com_fogo"),
        sand.rename("areia_pct"),
        ndvi26.rename("ndvi_jun_out_2026"),
        rain_wet.rename("chuva_jan_mai_2026"),
        rain_dry.rename("chuva_jun_out_2026"),
        temp,
    ])


def main() -> None:
    import ee
    from scipy.stats import kruskal, spearmanr

    from pipeline.tese import _points, nisar_features

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    pts = _points("poligonos").merge(nisar_features("poligonos"), on="id").dropna(subset=["nisar_hv_db"])
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"id": int(r.id)}) for r in pts.itertuples()])
    sampled = covariates().reduceRegions(fc, ee.Reducer.first(), scale=30, tileScale=4).getInfo()["features"]
    cov = pd.DataFrame([f["properties"] for f in sampled])
    df = pts.merge(cov, on="id")
    # tendência MODIS 2001–2024 (RESTREND) já calculada localmente
    import rasterio
    df["ndvi_tendencia_2001_2024"] = np.nan
    for area in ("serido", "sao_francisco"):
        with rasterio.open(DATA_PROCESSED / "poligonos" / f"gee_{area}.tif") as src:
            sel = df.regiao == area
            vals = np.array([v[1] for v in src.sample(list(zip(df.lon[sel], df.lat[sel])))], float) / 1e5
            df.loc[sel, "ndvi_tendencia_2001_2024"] = vals
    df["desmatado_2001_2024"] = (df.ano_desmatamento > 0).astype(int)
    df["pastagem_vigor_baixo"] = (df.vigor_pastagem_2024 == 1).astype(int)
    df.loc[df.temp_jun_out_2026 == -999, "temp_jun_out_2026"] = np.nan
    df.to_csv(OUT / "correlacoes_nisar_pontos.csv", index=False)

    nis = list(NISAR_LABELS)
    others = ["ndvi_jun_out_2026", "ndvi_tendencia_2001_2024", "desmatado_2001_2024", "pastagem_vigor_baixo",
              "veg_secundaria_2024", "anos_com_fogo", "areia_pct", "chuva_jan_mai_2026", "chuva_jun_out_2026",
              "temp_jun_out_2026"]
    others = [o for o in others if df[o].notna().sum() > 50 and df[o].nunique() > 1]
    rho = pd.DataFrame(index=[NISAR_LABELS[n] for n in nis], columns=others, dtype=float)
    pval = rho.copy()
    for n in nis:
        for o in others:
            ok = df[[n, o]].dropna()
            r = spearmanr(ok[n], ok[o])
            rho.loc[NISAR_LABELS[n], o], pval.loc[NISAR_LABELS[n], o] = r.statistic, r.pvalue
    rho.round(3).to_csv(OUT / "correlacoes_nisar_spearman.csv")

    df["classe_mapbiomas"] = df.mapbiomas_2024.map(CLASSES).fillna("outra")
    by_class = (df.groupby("classe_mapbiomas")
                .agg(pontos=("id", "size"), HV_dB=("nisar_hv_db", "median"), HH_dB=("nisar_hh_db", "median"),
                     HVHH_dB=("nisar_hvhh_db", "median"), RVI=("nisar_rvi", "median"), HV_textura=("nisar_hv_tex", "median"),
                     NDVI_2026=("ndvi_jun_out_2026", "median"))
                .query("pontos >= 20").sort_values("HV_dB", ascending=False))
    groups = [g.nisar_hv_db.values for _, g in df.groupby("classe_mapbiomas") if len(g) >= 20]
    kw = kruskal(*groups)
    by_class.round(3).to_csv(OUT / "correlacoes_nisar_por_classe.csv")

    def fmt(r, p):
        star = "**" if p < 0.001 and abs(r) >= 0.3 else ""
        return f"{star}{r:+.2f}{star}" + ("" if p < 0.05 else " (ns)")

    L = ["# Indicadores NISAR (jun–out/2026) × MapBiomas e outras camadas", "",
         f"Pontos: {len(df)} em 14 municípios (Seridó e São Francisco). Correlação de Spearman (ρ).",
         "Negrito: |ρ| ≥ 0,30 e p < 0,001. (ns) = não significativo (p ≥ 0,05).", "",
         "| Indicador NISAR | " + " | ".join(others) + " |", "|---|" + "---|" * len(others)]
    for idx in rho.index:
        L.append(f"| {idx} | " + " | ".join(fmt(rho.loc[idx, o], pval.loc[idx, o]) for o in others) + " |")
    L += ["", f"## NISAR por classe de uso do MapBiomas 2024 (medianas; Kruskal-Wallis HV: H = {kw.statistic:.0f}, p = {kw.pvalue:.1g})", "",
          by_class.round(2).to_markdown(), ""]
    report = "\n".join(L)
    (OUT / "correlacoes_nisar.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
