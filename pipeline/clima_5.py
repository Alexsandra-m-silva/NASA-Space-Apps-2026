"""Chuva, temperatura e aridez por município, 1991–2024 (GEE).

- Chuva: CHIRPS (mm/ano).
- Temperatura média do ar a 2 m e evapotranspiração potencial: ERA5-Land mensal.
- Índice de aridez (UNEP) = chuva / evapotranspiração potencial.
  < 0,20 árido · 0,21–0,50 semiárido · 0,51–0,65 subúmido seco.
- Tendência: Sen (por década) e Mann-Kendall.

Uso: python -m pipeline.clima_5
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
FIVE = {"Floresta": "PE", "Currais Novos": "RN", "Parelhas": "RN", "Petrolina": "PE", "Casa Nova": "BA"}
YEARS = list(range(1991, 2025))
OUT = DATA_PROCESSED / "final_5"


def main() -> None:
    import ee
    from scipy.stats import kendalltau, theilslopes

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    aoi = [f for f in json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))["features"]
           if f["properties"]["municipio"] in FIVE]
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry(f["geometry"]), {"mun": f'{f["properties"]["municipio"]}/{f["properties"]["uf"]}'})
                               for f in aoi])
    era = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")

    def year_img(y):
        s, e = f"{y}-01-01", f"{y + 1}-01-01"
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum().rename("chuva_mm")
        m = era.filterDate(s, e)
        temp = m.select("temperature_2m").mean().subtract(273.15).rename("temp_c")
        tmax = m.select("temperature_2m_max").mean().subtract(273.15).rename("tmax_c")
        pet = m.select("potential_evaporation_sum").sum().multiply(-1000).rename("etp_mm")  # m, negativo = evaporação
        return rain.addBands([temp, tmax, pet])

    rows = []
    for y in YEARS:
        res = year_img(y).reduceRegions(fc, ee.Reducer.mean(), scale=5000).getInfo()
        for f in res["features"]:
            rows.append({"municipio": f["properties"]["mun"], "ano": y} |
                        {k: f["properties"].get(k) for k in ("chuva_mm", "temp_c", "tmax_c", "etp_mm")})
        print(y, end=" ", flush=True)
    print()
    df = pd.DataFrame(rows)
    df["aridez"] = df.chuva_mm / df.etp_mm
    df.to_csv(OUT / "clima_anual_1991_2024.csv", index=False)

    out = []
    for mun, g in df.groupby("municipio"):
        r = {"municipio": mun}
        for var, scale in [("chuva_mm", 10), ("temp_c", 10), ("tmax_c", 10), ("etp_mm", 10), ("aridez", 10)]:
            s = theilslopes(g[var], g.ano)[0] * scale
            p = kendalltau(g.ano, g[var]).pvalue
            r[f"{var}_tend_decada"] = round(s, 3 if var == "aridez" else 2)
            r[f"{var}_p"] = round(p, 3)
        a1, a2 = g[g.ano <= 2007], g[g.ano >= 2008]
        r["aridez_1991_2007"] = round(a1.chuva_mm.sum() / a1.etp_mm.sum(), 3)
        r["aridez_2008_2024"] = round(a2.chuva_mm.sum() / a2.etp_mm.sum(), 3)
        r["temp_media_1991_2007"] = round(a1.temp_c.mean(), 2)
        r["temp_media_2008_2024"] = round(a2.temp_c.mean(), 2)
        r["chuva_media_1991_2007"] = round(a1.chuva_mm.mean())
        r["chuva_media_2008_2024"] = round(a2.chuva_mm.mean())
        out.append(r)
    t = pd.DataFrame(out).set_index("municipio")
    t.to_csv(OUT / "clima_tendencias_5.csv")
    pd.set_option("display.width", 250)
    cols = ["chuva_media_1991_2007", "chuva_media_2008_2024", "chuva_mm_tend_decada", "chuva_mm_p",
            "temp_media_1991_2007", "temp_media_2008_2024", "temp_c_tend_decada", "temp_c_p",
            "aridez_1991_2007", "aridez_2008_2024", "aridez_tend_decada", "aridez_p"]
    print(t[cols].to_string())


if __name__ == "__main__":
    main()
