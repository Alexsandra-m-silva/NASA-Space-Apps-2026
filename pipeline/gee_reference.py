"""Rótulo de referência (sem NISAR) para testar a tese, via Google Earth Engine.

Para cada ponto amostrado nos núcleos:
- RESTREND: NDVI integrado anual (MODIS MOD13Q1, 2001–2025) explicado pela
  chuva anual (CHIRPS). A tendência (Sen) e o Mann-Kendall dos RESÍDUOS
  separam degradação de seca: queda de NDVI que a chuva não explica.
- MapBiomas: classe no início e no fim da série (transição para solo exposto
  ou pastagem é sinal de degradação).
- PALSAR/PALSAR-2 HV anual (JAXA, banda L como o NISAR): tendência 2015–2024,
  a "ponte" histórica para o NISAR.

Saída: data/processed/reference_points.csv (um ponto por linha).

Uso:
    python -m pipeline.gee_reference --project SEU_PROJETO_GCP [--points 3000]
"""

from __future__ import annotations

import argparse
import json

import ee
import pandas as pd

from pipeline.config import DATA_PROCESSED

YEARS = list(range(2001, 2026))
MODIS = "MODIS/061/MOD13Q1"
CHIRPS = "UCSB-CHG/CHIRPS/PENTAD"
PALSAR = "JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH"
MAPBIOMAS = "projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1"
MAPBIOMAS_FIRST, MAPBIOMAS_LAST = 2000, 2023
SCALE = 250


def annual_stack() -> ee.ImageCollection:
    def one(year):
        year = ee.Number(year)
        start = ee.Date.fromYMD(year, 1, 1)
        end = start.advance(1, "year")
        ndvi = (ee.ImageCollection(MODIS).filterDate(start, end)
                .map(lambda i: i.select("NDVI").multiply(0.0001)
                     .updateMask(i.select("SummaryQA").lte(1)))
                .mean().rename("ndvi"))
        rain = ee.ImageCollection(CHIRPS).filterDate(start, end).sum().rename("rain")
        t = ee.Image.constant(year).toFloat().rename("t")
        return ndvi.addBands(rain).addBands(t).set("year", year)
    return ee.ImageCollection(ee.List(YEARS).map(one))


def restrend(stack: ee.ImageCollection) -> ee.Image:
    # ndvi = a + b*rain por pixel; resíduo anual; tendência do resíduo no tempo.
    fit = stack.select(["rain", "ndvi"]).reduce(ee.Reducer.linearFit())
    a, b = fit.select("offset"), fit.select("scale")

    def residual(img):
        r = img.select("ndvi").subtract(a.add(b.multiply(img.select("rain")))).rename("resid")
        return r.addBands(img.select("t"))
    res = stack.map(residual)
    sens = res.select(["t", "resid"]).reduce(ee.Reducer.sensSlope()).select("slope").rename("resid_slope")
    mk = res.select(["t", "resid"]).reduce(ee.Reducer.kendallsCorrelation(2))
    ndvi_slope = stack.select(["t", "ndvi"]).reduce(ee.Reducer.sensSlope()).select("slope").rename("ndvi_slope")
    rue_r2 = stack.select(["rain", "ndvi"]).reduce(ee.Reducer.pearsonsCorrelation()).select("correlation").rename("ndvi_rain_r")
    return (sens.addBands(mk.select("resid_tau").rename("resid_tau"))
            .addBands(mk.select("resid_p-value").rename("resid_p"))
            .addBands(ndvi_slope).addBands(rue_r2)
            .addBands(stack.select("ndvi").mean().rename("ndvi_mean"))
            .addBands(stack.select("rain").mean().rename("rain_mean")))


def palsar_hv() -> ee.Image:
    col = ee.ImageCollection(PALSAR).filterDate("2015-01-01", "2025-01-01").select("HV")

    def db(img):
        # JAXA: gamma0 (dB) = 10*log10(DN^2) - 83.0
        hv = img.pow(2).log10().multiply(10).subtract(83).rename("hv_db")
        year = ee.Date(img.get("system:time_start")).get("year")
        return hv.addBands(ee.Image.constant(year).toFloat().rename("t"))
    col = col.map(db)
    slope = col.select(["t", "hv_db"]).reduce(ee.Reducer.sensSlope()).select("slope").rename("palsar_hv_slope")
    last = col.sort("system:time_start", False).first().select("hv_db").rename("palsar_hv_last")
    return slope.addBands(last)


def mapbiomas() -> ee.Image:
    img = ee.Image(MAPBIOMAS)
    return (img.select(f"classification_{MAPBIOMAS_FIRST}").rename("lc_first")
            .addBands(img.select(f"classification_{MAPBIOMAS_LAST}").rename("lc_last")))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, help="ID do projeto Google Cloud registrado no Earth Engine")
    p.add_argument("--points", type=int, default=3000, help="pontos por núcleo")
    args = p.parse_args()
    ee.Initialize(project=args.project)

    gj = json.loads((DATA_PROCESSED / "nucleos_municipios.geojson").read_text(encoding="utf-8"))
    image = restrend(annual_stack()).addBands(palsar_hv()).addBands(mapbiomas())

    frames = []
    for nucleo in sorted({f["properties"]["nucleo"] for f in gj["features"]}):
        feats = [f for f in gj["features"] if f["properties"]["nucleo"] == nucleo]
        region = ee.FeatureCollection([ee.Feature(ee.Geometry(f["geometry"]), f["properties"]) for f in feats]).geometry()
        # getInfo aceita até 5000 elementos; amostramos em lotes.
        done, seed = 0, 0
        while done < args.points:
            n = min(2000, args.points - done)
            fc = image.sample(region=region, scale=SCALE, numPixels=n * 2, seed=seed, geometries=True, tileScale=4).limit(n)
            rows = fc.getInfo()["features"]
            for r in rows:
                props = r["properties"]
                props["lon"], props["lat"] = r["geometry"]["coordinates"]
                props["nucleo"] = nucleo
            frames.append(pd.DataFrame([r["properties"] for r in rows]))
            done += len(rows)
            seed += 1
            print(f"{nucleo}: {done} pontos")
            if not rows:
                break

    df = pd.concat(frames, ignore_index=True)
    # Rótulo de referência: queda de NDVI que a chuva não explica, significativa.
    df["ref_degraded"] = ((df["resid_slope"] < 0) & (df["resid_p"] < 0.05)).astype(int)
    df["ref_improving"] = ((df["resid_slope"] > 0) & (df["resid_p"] < 0.05)).astype(int)
    out = DATA_PROCESSED / "reference_points.csv"
    df.to_csv(out, index=False)
    print(out, len(df))
    print(df.groupby("nucleo")[["ref_degraded", "ref_improving"]].mean().round(3))


if __name__ == "__main__":
    main()
