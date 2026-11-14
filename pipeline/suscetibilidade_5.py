"""Suscetibilidade à desertificação sob estresse climático (5 municípios, 250 m).

Índice = média de 5 componentes normalizados 0–1 (1 = mais suscetível), pesos iguais:
  1. Aquecimento     tendência da temperatura do ar 1991–2024 (ERA5-Land, °C/década)
  2. Aridez          chuva / evapotranspiração potencial 2008–2024 (CHIRPS / ERA5-Land); invertido
  3. Vegetação       tendência do NDVI descontada a chuva 2001–2024 (MODIS RESTREND); invertido
  4. Pressão de uso  fração do pixel com desmatamento 2001–2024 ou pastagem de vigor baixo (MapBiomas)
  5. Solo            fração de areia 0–30 cm (MapBiomas Solo); solos arenosos erodem mais
Normalização: percentis 2–98 dentro dos 5 municípios. Classes: quartis (baixa, média, alta, muito alta).
Validação: probabilidade de degradação estimada pelo NISAR (gradient boosting, fora da amostra) por classe.

Uso: python -m pipeline.suscetibilidade_5
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
FIVE = {"Floresta": "PE", "Currais Novos": "RN", "Parelhas": "RN", "Petrolina": "PE", "Casa Nova": "BA"}
OUT = DATA_PROCESSED / "final_5"
B = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_"
SAND = "projects/mapbiomas-public/assets/brazil/soil/collection3/mapbiomas_brazil_collection3_soil_sand_fraction_v1"
COMPONENTS = ["aquecimento", "aridez", "vegetacao", "pressao_uso", "solo_arenoso"]


def layers():
    import ee

    era = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
    yrs = list(range(1991, 2025))
    temp = ee.ImageCollection([era.filterDate(f"{y}-01-01", f"{y+1}-01-01").select("temperature_2m").mean()
                               .subtract(273.15).rename("v").addBands(ee.Image.constant(y).toFloat().rename("t"))
                               .toFloat() for y in yrs])
    warm = temp.select(["t", "v"]).reduce(ee.Reducer.sensSlope()).select("slope").multiply(10).rename("aquecimento")
    s, e = "2008-01-01", "2025-01-01"
    rain = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum()
    pet = era.filterDate(s, e).select("potential_evaporation_sum").sum().multiply(-1000)
    arid = rain.divide(pet).rename("aridez")
    lulc = ee.Image(B + "deforestation_secondary_vegetation_v2")
    defo = ee.ImageCollection([lulc.select(f"classification_{y}").remap([4, 6], [1, 1], 0).toUint8().rename("v")
                               for y in range(2001, 2025)]).max()
    vig = ee.Image(B + "pasture_vigor_v3")
    low = ee.ImageCollection([vig.select(f"classification_{y}").eq(1).unmask(0).toUint8().rename("v")
                              for y in range(2020, 2025)]).sum().gte(4)
    press = defo.Or(low).unmask(0).toFloat().rename("pressao_uso")
    sand_img = ee.ImageCollection(SAND).mosaic()
    sand = sand_img.select([0]).toFloat().rename("solo_arenoso")
    return warm, arid, press, sand


def main() -> None:
    import ee
    import rasterio
    from rasterio.features import geometry_mask, shapes, sieve
    from rasterio.warp import Resampling, reproject
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    from pyproj import Geod

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    geod = Geod(ellps="WGS84")
    aoi = [f for f in json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))["features"]
           if f["properties"]["municipio"] in FIVE]
    warm, arid, press, sand = layers()
    stack = ee.Image.cat([warm, arid, press, sand])
    feats_out, rows, arrays = [], [], {}

    for area in ("sao_francisco", "serido"):
        fs = [f for f in aoi if f["properties"]["area"] == area]
        geom = unary_union([shape(f["geometry"]) for f in fs]).buffer(0.01)
        region = ee.Geometry(mapping(geom.envelope))
        # grade MODIS já usada no RESTREND
        with rasterio.open(DATA_PROCESSED / "poligonos" / f"gee_{area}.tif") as src:
            sen = src.read(2).astype(float) / 1e5  # banda 'sen' x1e5 (ver pipeline.poligonos.gee_map)
            transform, crs, shp = src.transform, src.crs, (src.height, src.width)
        url = stack.toFloat().getDownloadURL(
            {"region": region, "scale": 250, "crs": "EPSG:4326", "format": "GEO_TIFF"})
        tif = OUT / f"camadas_{area}.tif"
        tif.write_bytes(requests.get(url, timeout=600).content)
        comp = {}
        with rasterio.open(tif) as src:
            for i, name in enumerate(["aquecimento", "aridez", "pressao_uso", "solo_arenoso"], 1):
                dst = np.full(shp, np.nan)
                reproject(src.read(i).astype(float), dst, src_transform=src.transform, src_crs=src.crs,
                          dst_transform=transform, dst_crs=crs, resampling=Resampling.bilinear)
                comp[name] = dst
        comp["vegetacao"] = np.where(np.isfinite(sen), sen, np.nan)
        mask = np.zeros(shp, bool)
        for f in fs:
            mask |= ~geometry_mask([f["geometry"]], out_shape=shp, transform=transform)
        arrays[area] = (comp, mask, transform, crs, fs)

    # normalização conjunta (percentis 2–98 nos 5 municípios); 1 = mais suscetível
    def pooled(name):
        return np.concatenate([a[0][name][a[1]] for a in arrays.values()])
    norm = {}
    for name in COMPONENTS:
        v = pooled(name)
        lo, hi = np.nanpercentile(v, [2, 98])
        invert = name in ("aridez", "vegetacao")
        norm[name] = (lo, hi, invert)
    idx_all = []
    for area, (comp, mask, transform, crs, fs) in arrays.items():
        parts = []
        for name in COMPONENTS:
            lo, hi, inv = norm[name]
            z = np.clip((comp[name] - lo) / (hi - lo), 0, 1)
            parts.append(1 - z if inv else z)
        idx = np.nanmean(np.stack(parts), axis=0)
        idx[~mask] = np.nan
        arrays[area] = (comp, mask, transform, crs, fs, idx, parts)
        idx_all.append(idx[mask])
    q = np.nanpercentile(np.concatenate(idx_all), [25, 50, 75])
    names = {1: "baixa", 2: "media", 3: "alta", 4: "muito_alta"}

    pts = pd.read_csv(DATA_PROCESSED / "tese_resultado" / "poligonos_pontos.csv")
    pts = pts[pts.municipio.isin(FIVE)].copy()
    pts["suscetibilidade"] = np.nan
    for area, (comp, mask, transform, crs, fs, idx, parts) in arrays.items():
        cls = np.digitize(idx, q) + 1
        cls = np.where(np.isfinite(idx), cls, 0).astype(np.uint8)
        prof = {"driver": "GTiff", "height": idx.shape[0], "width": idx.shape[1], "count": 2, "dtype": "float32",
                "crs": crs, "transform": transform, "compress": "deflate", "nodata": np.nan}
        with rasterio.open(OUT / f"suscetibilidade_{area}.tif", "w", **prof) as dst:
            dst.write(np.stack([idx, cls]).astype("float32"))
        # pontos NISAR: índice no pixel
        inv = ~transform
        for i, r in pts.iterrows():
            c, rr = inv * (r.lon, r.lat)
            c, rr = int(c), int(rr)
            if 0 <= rr < idx.shape[0] and 0 <= c < idx.shape[1] and np.isfinite(idx[rr, c]):
                pts.at[i, "suscetibilidade"] = idx[rr, c]
        for f in fs:
            m = ~geometry_mask([f["geometry"]], out_shape=idx.shape, transform=transform)
            key = f'{f["properties"]["municipio"]}/{f["properties"]["uf"]}'
            row = {"municipio": key, "indice_medio": round(float(np.nanmean(idx[m])), 3)}
            for k, n in names.items():
                row[f"pct_{n}"] = round(100 * float((cls[m] == k).sum()) / m.sum(), 1)
            for name, part in zip(COMPONENTS, parts):
                row[f"comp_{name}"] = round(float(np.nanmean(part[m])), 2)
            rows.append(row)
            for k in (3, 4):
                sm = sieve(((cls == k) & m).astype(np.uint8), size=4, connectivity=8)
                for g, _ in shapes(sm, mask=sm.astype(bool), transform=transform, connectivity=8):
                    ha = abs(geod.geometry_area_perimeter(shape(g))[0]) / 1e4
                    feats_out.append({"type": "Feature", "geometry": g, "properties": {
                        "municipio": key, "suscetibilidade": names[k], "area_ha": round(ha, 1)}})

    (OUT / "suscetibilidade_alta_5municipios.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats_out}, ensure_ascii=False), encoding="utf-8")
    t = pd.DataFrame(rows).set_index("municipio").sort_values("indice_medio", ascending=False)
    t.to_csv(OUT / "suscetibilidade_5.csv")

    # validação NISAR
    from scipy.stats import spearmanr
    v = pts.dropna(subset=["suscetibilidade"]).copy()
    v["classe_susc"] = pd.cut(v.suscetibilidade, [-np.inf, *q, np.inf], labels=list(names.values()))
    val = v.groupby("classe_susc", observed=True).agg(pontos=("prob_nisar", "size"), prob_degradacao_nisar=("prob_nisar", "mean"),
                                                      pct_degradado_modis=("classe", lambda s: 100 * (s == "degradado").mean()))
    rho = spearmanr(v.suscetibilidade, v.prob_nisar)
    val.round(3).to_csv(OUT / "suscetibilidade_validacao_nisar.csv")
    pd.set_option("display.width", 250)
    print(t.to_string()); print()
    print(val.round(3).to_string())
    print(f"Spearman índice x prob. NISAR: rho={rho.statistic:.3f} p={rho.pvalue:.2g} n={len(v)}")
    print(len(feats_out), "polígonos alta/muito alta")


if __name__ == "__main__":
    main()
