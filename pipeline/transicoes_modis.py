"""O que aconteceu (MapBiomas 2001 -> 2024) nos pixels que o MODIS marcou como degradados?

Separa a degradação compatível com desertificação (Caatinga que virou pastagem fraca,
solo exposto ou continuou Caatinga perdendo verde) de mudanças de uso que não são
desertificação (lavoura irrigada, usina solar, urbano, água).

Uso: python -m pipeline.transicoes_modis
"""

from __future__ import annotations

import json
import os

import pandas as pd
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
LULC = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_integration_v2"
NATIVE = {3, 4, 5, 6, 11, 12, 13, 49, 50}
GROUPS = {
    "Caatinga continua Caatinga (perda de vigor/densidade)": lambda a, b: a in NATIVE and b in NATIVE,
    "Caatinga -> pastagem / mosaico de usos": lambda a, b: a in NATIVE and b in {15, 21},
    "Caatinga -> solo exposto": lambda a, b: a in NATIVE and b in {25},
    "Caatinga -> lavoura": lambda a, b: a in NATIVE and b in {20, 39, 40, 41, 46, 47, 48, 62},
    "Caatinga -> usina solar / urbano / mineração": lambda a, b: a in NATIVE and b in {75, 24, 30},
    "Já era uso antrópico em 2001": lambda a, b: a not in NATIVE and a not in {33},
    "Água / outros": lambda a, b: True,
}


def main() -> None:
    import ee
    from shapely.geometry import mapping, shape

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    lulc = ee.Image(LULC)
    trans = lulc.select("classification_2001").multiply(1000).add(lulc.select("classification_2024")).rename("tr")
    aoi = json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))["features"]
    rows = []
    for area in ("serido", "sao_francisco"):
        # classes MODIS (250 m) já calculadas localmente -> sobe como polígonos degradados por município
        degr = json.loads((DATA_PROCESSED / "poligonos" / f"poligonos_{area}.geojson").read_text())["features"]
        degr = [shape(f["geometry"]) for f in degr if f["properties"]["classe"] == "degradado"]
        for f in aoi:
            if f["properties"]["area"] != area:
                continue
            mun = shape(f["geometry"])
            parts = [g.intersection(mun) for g in degr if g.intersects(mun)]
            parts = [p for p in parts if not p.is_empty and p.area > 0]
            key = f'{f["properties"]["municipio"]}/{f["properties"]["uf"]}'
            if not parts:
                rows.append({"municipio": key, "ha_total": 0})
                continue
            fc = ee.FeatureCollection([ee.Feature(ee.Geometry(mapping(p))) for p in parts])
            hist = trans.reduceRegion(ee.Reducer.frequencyHistogram(), fc.geometry(), scale=30,
                                      maxPixels=1e10, tileScale=4).getInfo()["tr"]
            out = {"municipio": key}
            for k, n in hist.items():
                a, b = divmod(int(float(k)), 1000)
                g = next(name for name, test in GROUPS.items() if test(a, b))
                out[g] = out.get(g, 0) + n * 0.09  # 30 m = 0,09 ha
            out["ha_total"] = sum(v for kk, v in out.items() if kk != "municipio")
            rows.append(out)
            print(key, round(out["ha_total"]), flush=True)
    df = pd.DataFrame(rows).fillna(0).set_index("municipio")
    pct = df[list(GROUPS)].div(df.ha_total.replace(0, 1), axis=0).mul(100).round(1)
    pct.insert(0, "ha_degradado_modis", df.ha_total.round(0))
    pct = pct.sort_values("ha_degradado_modis", ascending=False)
    out = DATA_PROCESSED / "poligonos" / "transicoes_degradado_modis.csv"
    pct.to_csv(out, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(pct.to_string())


if __name__ == "__main__":
    main()
