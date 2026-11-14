"""Polígonos de degradação vegetal a 30 m por município (Landsat 2001–2024, RESTREND).

Mesmo método do mapa MODIS (pipeline.poligonos), agora com Landsat:
- NDVI anual = mediana das observações sem nuvem (Landsat 5, 7, 8, 9 Collection 2 L2).
  OLI (8/9) harmonizado para ETM+ (Roy et al. 2016, coeficientes OLS do vermelho e do NIR).
- Chuva anual CHIRPS. RESTREND: resíduo NDVI ~ chuva; tendência de Sen e Mann-Kendall do resíduo.
- Degradado: tendência negativa com p < 0,05. Melhora: positiva com p < 0,05.
- Fora: água, urbano, mineração, usina solar e lavouras (MapBiomas 2024).
- Polígonos com >= 11 pixels (~1 ha).

Uso:
    python -m pipeline.degradacao_30m download
    python -m pipeline.degradacao_30m polygons
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
OUT = DATA_PROCESSED / "degradacao_30m"
YEARS = list(range(2001, 2025))
TILE = 0.25
MAPBIOMAS10 = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_integration_v2"
EXCLUDE = [33, 24, 30, 75, 39, 40, 41, 46, 47, 48, 62, 20]


def _ndvi_collection():
    import ee

    def mask_l2(img):
        qa = img.select("QA_PIXEL")
        clear = qa.bitwiseAnd(0b11111).eq(0)  # fill, dilated cloud, cirrus, cloud, shadow
        return img.updateMask(clear)

    def tm_etm(img):
        sr = img.select(["SR_B3", "SR_B4"]).multiply(0.0000275).add(-0.2)
        return sr.normalizedDifference(["SR_B4", "SR_B3"]).toFloat().rename("ndvi").copyProperties(img, ["system:time_start"])

    def oli(img):
        # Roy et al. (2016) dão ETM+ -> OLI (OLI = a*ETM + b); aqui aplicamos o inverso.
        sr = img.select(["SR_B4", "SR_B5"]).multiply(0.0000275).add(-0.2)
        red = sr.select("SR_B4").subtract(0.0061).divide(0.9047)
        nir = sr.select("SR_B5").subtract(0.0412).divide(0.8462)
        return nir.subtract(red).divide(nir.add(red)).toFloat().rename("ndvi").copyProperties(img, ["system:time_start"])

    l5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").map(mask_l2).map(tm_etm)
    l7 = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterDate("1999-01-01", "2022-04-01").map(mask_l2).map(tm_etm)
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").map(mask_l2).map(oli)
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").map(mask_l2).map(oli)

    # Calibração cruzada por pixel: nos anos em que L7 e L8 operaram juntos, a diferença
    # mediana (L8 - L7) do NDVI anual é descontada de L8/L9. Mesmo após Roy inverso sobrava
    # +0,02 a +0,05 de viés regional, o suficiente para criar falsa tendência de "melhora".
    diffs = [l8.filterDate(f"{y}-01-01", f"{y + 1}-01-01").median()
             .subtract(l7.filterDate(f"{y}-01-01", f"{y + 1}-01-01").median()).rename("d")
             for y in range(2014, 2021)]
    offset = ee.ImageCollection(diffs).median().unmask(0)

    def corr(img):
        return img.subtract(offset).toFloat().rename("ndvi").copyProperties(img, ["system:time_start"])

    return l5.merge(l7).merge(l8.map(corr)).merge(l9.map(corr))


def _image(region):
    import ee

    col = _ndvi_collection().filterBounds(region)

    def annual(y):
        y = ee.Number(y)
        s = ee.Date.fromYMD(y, 1, 1)
        e = s.advance(1, "year")
        ndvi = col.filterDate(s, e).median().rename("ndvi")
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum().rename("rain")
        return ndvi.addBands(rain).addBands(ee.Image.constant(y).toFloat().rename("t"))

    stack = ee.ImageCollection(ee.List(YEARS).map(annual))
    fit = stack.select(["rain", "ndvi"]).reduce(ee.Reducer.linearFit())
    res = stack.map(lambda i: i.select("ndvi").subtract(fit.select("offset").add(fit.select("scale").multiply(i.select("rain"))))
                    .rename("resid").addBands(i.select("t")))
    sen = res.select(["t", "resid"]).reduce(ee.Reducer.sensSlope()).select("slope")
    tau = res.select(["t", "resid"]).reduce(ee.Reducer.kendallsCorrelation(2)).select("tau")
    n = res.select("resid").count()
    sd = n.multiply(2).add(5).multiply(2).divide(n.multiply(n.subtract(1)).multiply(9)).sqrt()
    z = tau.divide(sd).abs()
    excl = ee.Image(MAPBIOMAS10).select("classification_2024").remap(EXCLUDE, [1] * len(EXCLUDE), 0)
    base = n.gte(15).And(excl.Not())
    cls = (ee.Image(0)
           .where(base.And(sen.lt(0)).And(z.gt(1.96)), 1)    # degradado
           .where(base.And(sen.gt(0)).And(z.gt(1.96)), 3)    # melhora
           .where(base.And(z.lt(0.674)), 2)                  # estável (controle)
           .toUint8().rename("cls"))
    # magnitude: queda de NDVI acumulada no período (Sen x anos), x1000
    mag = sen.multiply(len(YEARS) - 1).multiply(1000).clamp(-127, 127).toInt8().rename("mag")
    return cls.addBands(mag)


def download() -> None:
    import ee
    from shapely.geometry import box, mapping, shape
    from shapely.ops import unary_union

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    aoi = json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))
    tiles = OUT / "tiles"
    tiles.mkdir(parents=True, exist_ok=True)
    jobs = []
    for area in ("serido", "sao_francisco", "comprovados"):
        geom = unary_union([shape(f["geometry"]) for f in aoi["features"] if f["properties"]["area"] == area]).buffer(0.003)
        minx, miny, maxx, maxy = geom.bounds
        for x in np.arange(np.floor(minx / TILE) * TILE, maxx, TILE):
            for y in np.arange(np.floor(miny / TILE) * TILE, maxy, TILE):
                t = box(x, y, x + TILE, y + TILE)
                if t.intersects(geom):
                    jobs.append((area, round(x, 3), round(y, 3), mapping(t.intersection(geom).envelope)))

    def fetch(job):
        area, x, y, g = job
        out = tiles / f"{area}_{x}_{y}.tif"
        if out.exists():
            return "já"
        region = ee.Geometry(g)
        for attempt in range(3):
            try:
                url = _image(region).clip(region).getDownloadURL(
                    {"region": region, "scale": 30, "crs": "EPSG:4326", "format": "GEO_TIFF"})
                r = requests.get(url, timeout=900)
                if r.content[:2] in (b"II", b"MM"):
                    out.write_bytes(r.content)
                    return "ok"
                err = r.text[:200]
            except Exception as e:  # tempo de computação do GEE
                err = str(e)[:200]
        return f"falhou {out.name}: {err}"

    print(len(jobs), "tiles", flush=True)
    with ThreadPoolExecutor(6) as ex:
        for res in ex.map(fetch, jobs):
            if res not in ("ok", "já"):
                print(res, flush=True)
    print("baixados:", len(list(tiles.glob("*.tif"))), "de", len(jobs))


def polygons() -> None:
    import pandas as pd
    import rasterio
    from pyproj import Geod
    from rasterio.features import geometry_mask, shapes, sieve
    from rasterio.merge import merge
    from shapely.geometry import mapping, shape

    geod = Geod(ellps="WGS84")
    aoi = json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))
    muns = [(f["properties"]["municipio"], f["properties"]["uf"], f["properties"]["area"], shape(f["geometry"]))
            for f in aoi["features"]]
    names = {1: "degradado", 2: "controle_estavel", 3: "melhora"}
    by_mun: dict[str, list] = {}
    resumo = {}
    for area in ("serido", "sao_francisco", "comprovados"):
        srcs = [rasterio.open(p) for p in sorted((OUT / "tiles").glob(f"{area}_*.tif"))]
        mosaic, transform = merge(srcs, nodata=0)
        prof = srcs[0].profile | {"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": transform,
                                  "compress": "deflate"}
        for s in srcs:
            s.close()
        cls, mag = mosaic[0].astype(np.uint8), mosaic[1].astype(np.int8)
        for nome, uf, a, g in muns:
            if a != area:
                continue
            key = f"{nome}/{uf}"
            inside = ~geometry_mask([mapping(g)], out_shape=cls.shape, transform=transform)
            px_ha = {}
            for code, cname in names.items():
                m = sieve(((cls == code) & inside).astype(np.uint8), size=11, connectivity=8)
                for geom, _ in shapes(m, mask=m.astype(bool), transform=transform, connectivity=8):
                    gg = shape(geom)
                    ha = abs(geod.geometry_area_perimeter(gg)[0]) / 1e4
                    px_ha[cname] = px_ha.get(cname, 0) + ha
                    if code == 1:
                        sel = geometry_mask([geom], out_shape=cls.shape, transform=transform, invert=True)
                        queda = float(np.median(mag[sel])) / 1000 if sel.any() else None
                        by_mun.setdefault(key, []).append({"type": "Feature", "geometry": geom, "properties": {
                            "municipio": nome, "uf": uf, "classe": cname, "area_ha": round(ha, 2),
                            "queda_ndvi_2001_2024": queda}})
            resumo[key] = {k: round(px_ha.get(k, 0)) for k in names.values()}
            print(key, resumo[key], flush=True)
        with rasterio.open(OUT / f"classes_30m_{area}.tif", "w", **(prof | {"count": 2})) as dst:
            dst.write(np.stack([cls, mag.view(np.uint8)]))

    per_dir = OUT / "por_municipio"
    per_dir.mkdir(exist_ok=True)
    allf = []
    for key, feats in by_mun.items():
        feats.sort(key=lambda f: -f["properties"]["area_ha"])
        for i, f in enumerate(feats, 1):
            f["properties"]["id"] = f"{key.replace('/', '-')}-{i:04d}"
        fname = key.replace("/", "_").replace(" ", "_")
        (per_dir / f"{fname}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                             ensure_ascii=False), encoding="utf-8")
        allf += feats
    (OUT / "degradacao_vegetal_30m.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": allf},
                                                                     ensure_ascii=False), encoding="utf-8")
    df = pd.DataFrame(resumo).T
    df["poligonos_degradados"] = [len(by_mun.get(k, [])) for k in df.index]
    df = df.sort_values("degradado", ascending=False)
    df.to_csv(OUT / "resumo_municipios.csv", encoding="utf-8")
    print(df.to_string())


if __name__ == "__main__":
    {"download": download, "polygons": polygons}[sys.argv[1]]()
