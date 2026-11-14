"""Polígonos de degradação por convergência de evidências (30 m, 2001–2024).

Cada pixel recebe um código de bits com as evidências que se confirmam nele:
  bit 1  (1)  DESMAT     supressão de vegetação nativa primária ou secundária em 2001–2024
                         (MapBiomas Col. 10, desmatamento e vegetação secundária: classes 4 e 6)
  bit 2  (2)  SOLO_EXP   era vegetação nativa em 2001 e é "outra área não vegetada" (25) em 2024
  bit 3  (4)  PAST_BAIXA pastagem com vigor BAIXO em >= 4 dos 5 anos 2020–2024 (MapBiomas vigor de pastagem)
  bit 4  (8)  NDVI_QUEDA queda de NDVI que a chuva não explica, 2001–2024 (MODIS + CHIRPS, RESTREND, p < 0,05)
  bit 5 (16)  FOGO_REC   queimado em >= 3 anos entre 2001 e 2024 (MapBiomas Fogo Col. 4)

Excluídos (não são desertificação): água (33), urbano (24), mineração (30),
usina fotovoltaica (75), lavouras (39, 40, 41, 46, 47, 48, 62, 20) em 2024.

Convergência: número de evidências no pixel. >= 2 = alta confiança.

Uso:
    python -m pipeline.evidencias download   # baixa os tiles do GEE
    python -m pipeline.evidencias polygons   # mosaica, vetoriza e resume por município
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
OUT = DATA_PROCESSED / "evidencias"
B = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_"
FIRE = "projects/mapbiomas-public/assets/brazil/fire/collection4/mapbiomas_fire_collection4_annual_burned_v1"
TILE = 0.25  # graus
BITS = {1: "desmatamento", 2: "solo_exposto", 4: "pastagem_vigor_baixo", 8: "queda_ndvi_modis", 16: "fogo_recorrente"}
NATIVE = [3, 4, 5, 6, 11, 12, 13, 49, 50]
EXCLUDE = [33, 24, 30, 75, 39, 40, 41, 46, 47, 48, 62, 20]


def _image():
    import ee

    years = list(range(2001, 2025))
    lulc = ee.Image(B + "integration_v2")
    defo = ee.Image(B + "deforestation_secondary_vegetation_v2")
    loss = ee.ImageCollection([defo.select(f"classification_{y}").remap([4, 6], [1, 1], 0).multiply(y - 2000).toUint8().rename("v").selfMask()
                               for y in years]).min().unmask(0)  # ano (2001=1) da primeira supressão
    e_desmat = loss.gt(0)
    native01 = lulc.select("classification_2001").remap(NATIVE, [1] * len(NATIVE), 0)
    e_solo = native01.And(lulc.select("classification_2024").eq(25))
    vigor = ee.Image(B + "pasture_vigor_v3")
    low = ee.ImageCollection([vigor.select(f"classification_{y}").eq(1).unmask(0).toUint8().rename("v") for y in range(2020, 2025)]).sum()
    e_past = low.gte(4)
    fire = ee.Image(FIRE)
    fire_bands = [b for b in fire.bandNames().getInfo() if b[-4:].isdigit() and 2001 <= int(b[-4:]) <= 2024]
    e_fogo = ee.ImageCollection([fire.select(b).gt(0).unmask(0).toUint8().rename("v") for b in fire_bands]).sum().gte(3)
    excl = lulc.select("classification_2024").remap(EXCLUDE, [1] * len(EXCLUDE), 0)
    code = (e_desmat.multiply(1).add(e_solo.multiply(2)).add(e_past.multiply(4)).add(e_fogo.multiply(16))
            .where(excl, 0).toUint8().rename("code"))
    return code.addBands(loss.toUint8().rename("loss_year")).addBands(excl.toUint8().rename("excluido"))


def download() -> None:
    import ee
    from shapely.geometry import box, mapping, shape
    from shapely.ops import unary_union

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    img = _image()
    aoi = json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))
    tiles_dir = OUT / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for area in ("serido", "sao_francisco"):
        geom = unary_union([shape(f["geometry"]) for f in aoi["features"] if f["properties"]["area"] == area]).buffer(0.003)
        minx, miny, maxx, maxy = geom.bounds
        for x in np.arange(np.floor(minx / TILE) * TILE, maxx, TILE):
            for y in np.arange(np.floor(miny / TILE) * TILE, maxy, TILE):
                t = box(x, y, x + TILE, y + TILE)
                if t.intersects(geom):
                    jobs.append((area, round(x, 3), round(y, 3), mapping(t.intersection(geom).envelope)))

    def fetch(job):
        area, x, y, g = job
        out = tiles_dir / f"{area}_{x}_{y}.tif"
        if out.exists():
            return
        url = img.clip(ee.Geometry(g)).getDownloadURL(
            {"region": ee.Geometry(g), "scale": 30, "crs": "EPSG:4326", "format": "GEO_TIFF"})
        r = requests.get(url, timeout=600)
        if r.content[:2] not in (b"II", b"MM"):  # assinatura TIFF
            raise RuntimeError(f"{out.name}: {r.text[:300]}")
        out.write_bytes(r.content)

    print(len(jobs), "tiles")
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(fetch, jobs))
    print("ok")


def polygons() -> None:
    import rasterio
    from pyproj import Geod
    from rasterio.features import shapes, sieve
    from rasterio.merge import merge
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

    geod = Geod(ellps="WGS84")
    aoi = json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))
    muns = [(f["properties"]["municipio"], f["properties"]["uf"], f["properties"]["area"], shape(f["geometry"]))
            for f in aoi["features"]]
    feats, resumo = [], {}
    for area in ("serido", "sao_francisco"):
        srcs = [rasterio.open(p) for p in sorted((OUT / "tiles").glob(f"{area}_*.tif"))]
        mosaic, transform = merge(srcs)
        profile = srcs[0].profile | {"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": transform,
                                     "count": 2, "compress": "deflate"}
        for s in srcs:
            s.close()
        code, loss, excl = mosaic[0].astype(np.uint8), mosaic[1], mosaic[2].astype(bool)

        # bit 4: NDVI MODIS degradado (classe 1 do RESTREND, 250 m) reamostrado para 30 m
        from rasterio.warp import Resampling, reproject
        modis = np.zeros_like(code)
        with rasterio.open(DATA_PROCESSED / "poligonos" / f"classes_{area}.tif") as m:
            reproject(m.read(1), modis, src_transform=m.transform, src_crs=m.crs, dst_transform=transform,
                      dst_crs="EPSG:4326", resampling=Resampling.nearest)
        code = code | np.where((modis == 1) & ~excl, 8, 0).astype(np.uint8)

        # máscara do recorte municipal
        from rasterio.features import geometry_mask
        inside = ~geometry_mask([mapping(g) for _, _, a, g in muns if a == area], out_shape=code.shape, transform=transform)
        code = np.where(inside, code, 0).astype(np.uint8)
        with rasterio.open(OUT / f"evidencias_{area}.tif", "w", **(profile | {"dtype": "uint8", "nodata": 0})) as dst:
            dst.write(np.stack([code, loss.astype(np.uint8)]))

        n_ev = np.zeros_like(code)
        for bit in BITS:
            n_ev += ((code & bit) > 0).astype(np.uint8)
        # Vetoriza por código, depois de remover manchas < 11 px (~1 ha)
        cleaned = sieve(np.where(n_ev > 0, code, 0).astype(np.int32), size=11, connectivity=8)
        for geom, val in shapes(cleaned.astype(np.int32), mask=cleaned > 0, transform=transform, connectivity=8):
            val = int(val)
            g = shape(geom)
            ev = [name for bit, name in BITS.items() if val & bit]
            ha = abs(geod.geometry_area_perimeter(g)[0]) / 1e4
            c = g.representative_point()
            mun = next((f"{n}/{u}" for n, u, a, m in muns if a == area and m.contains(c)), None)
            feats.append({"type": "Feature", "geometry": geom,
                          "properties": {"regiao": area, "municipio": mun, "codigo": val, "evidencias": ",".join(ev),
                                         "n_evidencias": len(ev), "confianca": "alta" if len(ev) >= 2 else "baixa",
                                         "area_ha": round(ha, 2)}})
            r = resumo.setdefault(mun, {"ha_1_evid": 0.0, "ha_2mais_evid": 0.0} | {k: 0.0 for k in BITS.values()})
            r["ha_2mais_evid" if len(ev) >= 2 else "ha_1_evid"] += ha
            for e in ev:
                r[e] += ha
        print(area, "polígonos:", sum(f["properties"]["regiao"] == area for f in feats), flush=True)

    (OUT / "poligonos_evidencias.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    alta = [f for f in feats if f["properties"]["n_evidencias"] >= 2]
    (OUT / "poligonos_alta_confianca.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": alta}, ensure_ascii=False), encoding="utf-8")
    import pandas as pd
    df = pd.DataFrame(resumo).T.sort_values("ha_2mais_evid", ascending=False).round(0)
    df.to_csv(OUT / "resumo_municipios.csv", encoding="utf-8")
    print(df.to_string())


if __name__ == "__main__":
    {"download": download, "polygons": polygons}[sys.argv[1]]()
