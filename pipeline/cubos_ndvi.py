"""Cubos para o "Comparar e explicar" pelo método do NDVI (5 municípios).

Grade de 0,01° (~1,1 km) cobrindo cada município. Para cada município grava
products/<slug>_ndvi.npz com:
  ndvi    [anos, linhas, colunas]   NDVI anual médio MODIS MOD13Q1 (QA bom), 2001–2024
  chuva   [anos, linhas, colunas]   chuva anual CHIRPS (mm), 2001–2024
  hv_db   [datas, linhas, colunas]  NISAR GCOV HV gamma0 (dB), uma órbita/quadro, 2026
  hh_db   [datas, linhas, colunas]  NISAR GCOV HH gamma0 (dB)
  anos, west, south, east, north, resolution
e products/<slug>_ndvi.json com metadados, série climática do município e datas NISAR.

Uso:
    python -m pipeline.cubos_ndvi modis            # NDVI + chuva (GEE)
    python -m pipeline.cubos_ndvi nisar <slug>     # HV/HH (Earthdata), um município
    python -m pipeline.cubos_ndvi build            # junta tudo nos .npz/.json
"""

from __future__ import annotations

import json
import os
import sys
import unicodedata

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
RES = 0.01
YEARS = list(range(2001, 2025))
PRODUCTS = ROOT / "products"
WORK = DATA_PROCESSED / "cubos_ndvi"
FIVE = {"Floresta": "PE", "Currais Novos": "RN", "Parelhas": "RN", "Petrolina": "PE", "Casa Nova": "BA"}
NISAR_PRODUCTS = ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_GCOV_V1")
GROUP = "science/LSAR/GCOV/grids/frequencyA"


def slugify(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(" ", "-")


def places():
    aoi = json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))["features"]
    from shapely.geometry import shape
    out = {}
    for f in aoi:
        nome = f["properties"]["municipio"]
        if nome in FIVE and nome not in [p["nome"] for p in out.values()]:
            g = shape(f["geometry"])
            minx, miny, maxx, maxy = g.bounds
            west, south = np.floor(minx / RES) * RES, np.floor(miny / RES) * RES
            east, north = np.ceil(maxx / RES) * RES, np.ceil(maxy / RES) * RES
            out[slugify(nome)] = {"nome": nome, "uf": FIVE[nome], "geom": g, "geojson": f["geometry"],
                                  "west": round(west, 4), "south": round(south, 4), "east": round(east, 4), "north": round(north, 4),
                                  "w": int(round((east - west) / RES)), "h": int(round((north - south) / RES))}
    return out


def _inside(p):
    from rasterio.features import geometry_mask
    from rasterio.transform import from_origin
    return ~geometry_mask([p["geojson"]], out_shape=(p["h"], p["w"]), transform=from_origin(p["west"], p["north"], RES, RES))


# ---------------------------------------------------------------- MODIS + CHIRPS (GEE)
def modis() -> None:
    import ee
    import rasterio

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    WORK.mkdir(parents=True, exist_ok=True)
    ndvi_bands, rain_bands = [], []
    for y in YEARS:
        s, e = f"{y}-01-01", f"{y + 1}-01-01"
        ndvi_bands.append(ee.ImageCollection("MODIS/061/MOD13Q1").filterDate(s, e)
                          .map(lambda i: i.select("NDVI").multiply(0.0001).updateMask(i.select("SummaryQA").lte(1)))
                          .mean().rename(f"ndvi_{y}"))
        rain_bands.append(ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum().rename(f"chuva_{y}"))
    for name, bands in (("ndvi", ndvi_bands), ("chuva", rain_bands)):
        img = ee.Image.cat(bands).toFloat()
        for slug, p in places().items():
            out = WORK / f"{slug}_{name}.tif"
            if out.exists():
                continue
            region = ee.Geometry.Rectangle([p["west"], p["south"], p["east"], p["north"]], None, False)
            url = img.getDownloadURL({"region": region, "crs": "EPSG:4326", "format": "GEO_TIFF",
                                      "crsTransform": [RES, 0, p["west"], 0, -RES, p["north"]],
                                      "dimensions": f"{p['w']}x{p['h']}"})
            r = requests.get(url, timeout=600)
            if r.content[:2] not in (b"II", b"MM"):
                raise SystemExit(f"{slug} {name}: {r.text[:300]}")
            out.write_bytes(r.content)
            with rasterio.open(out) as src:
                print(slug, name, src.count, src.shape, flush=True)


# ---------------------------------------------------------------- NISAR GCOV (Earthdata)
def _tf(ur: str) -> str:
    p = ur.split("_")
    return f"{p[5]}_{p[6]}_{p[7]}"


def _poly(g):
    from shapely.geometry import Polygon
    pts = g["umm"]["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]["GPolygons"][0]["Boundary"]["Points"]
    return Polygon([(q["Longitude"], q["Latitude"]) for q in pts])


def nisar(slug: str) -> None:
    import earthaccess
    import h5py
    from pyproj import Transformer

    p = places()[slug]
    earthaccess.login(strategy="environment")
    grans = []
    for prod in NISAR_PRODUCTS:
        grans += [g for g in earthaccess.search_data(short_name=prod, bounding_box=(p["west"], p["south"], p["east"], p["north"]),
                                                     count=500) if "_DHDH_" in g["umm"]["GranuleUR"]]
    by_tf = {}
    for g in grans:
        by_tf.setdefault(_tf(g["umm"]["GranuleUR"]), []).append(g)
    # órbita/quadro que mais cobre o município; desempate pelo número de datas
    score = {tf: (_poly(gs[0]).intersection(p["geom"]).area / p["geom"].area, len(gs)) for tf, gs in by_tf.items()}
    tf = max(score, key=lambda k: (round(score[k][0], 2), score[k][1]))
    chosen = sorted(by_tf[tf], key=lambda g: g["umm"]["GranuleUR"].split("_")[11])
    # uma cena por data (provisório e V1 podem repetir a mesma passagem)
    seen, uniq = set(), []
    for g in chosen:
        d = g["umm"]["GranuleUR"].split("_")[11][:8]
        if d not in seen:
            seen.add(d)
            uniq.append(g)
    # Municípios grandes: NISAR_DATAS_MAX limita a N datas espaçadas (cada cena lê uma janela de ~100 km)
    max_dates = int(os.environ.get("NISAR_DATAS_MAX", "0"))
    if max_dates and len(uniq) > max_dates:
        keep = sorted(set(np.linspace(0, len(uniq) - 1, max_dates).round().astype(int)))
        uniq = [uniq[k] for k in keep]
    print(slug, "órbita/quadro", tf, "cobertura", f"{score[tf][0]:.0%}", "datas", len(uniq), flush=True)

    lon = p["west"] + RES * (np.arange(p["w"]) + 0.5)
    lat = p["north"] - RES * (np.arange(p["h"]) + 0.5)
    LON, LAT = np.meshgrid(lon, lat)
    inside = _inside(p)
    outdir = WORK / f"{slug}_nisar"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "orbita.txt").write_text(tf)
    for g in uniq:
        d = g["umm"]["GranuleUR"].split("_")[11][:8]
        out = outdir / f"{d}.npz"
        if out.exists():
            print(slug, d, "células válidas: já extraída", flush=True)
            continue
        try:
            f = earthaccess.open([g])[0]
            with h5py.File(f, "r") as h:
                grp = h[GROUP]
                x, y = grp["xCoordinates"][()], grp["yCoordinates"][()]
                tr = Transformer.from_crs(4326, int(grp["projection"].attrs["epsg_code"]), always_xy=True)
                px, py = tr.transform(LON, LAT)
                dx, dy = x[1] - x[0], y[1] - y[0]
                col = np.round((px - x[0]) / dx).astype(int)
                row = np.round((py - y[0]) / dy).astype(int)
                half = int(round(RES * 111320 / 2 / abs(dx)))
                ok = inside & (col >= half) & (col < len(x) - half) & (row >= half) & (row < len(y) - half)
                if not ok.any():
                    print(slug, d, "fora do quadro", flush=True)
                    continue
                r0, r1 = row[ok].min() - half, row[ok].max() + half + 1
                c0, c1 = col[ok].min() - half, col[ok].max() + half + 1
                hv = grp["HVHV"][r0:r1, c0:c1]
                hh = grp["HHHH"][r0:r1, c0:c1]
                mask = grp["mask"][r0:r1, c0:c1]
        except Exception as e:
            print(slug, d, "falhou:", type(e).__name__, str(e)[:120], flush=True)
            continue
        valid = (mask > 0) & (mask < 255) & np.isfinite(hv) & (hv > 0) & np.isfinite(hh) & (hh > 0)
        HV = np.full(inside.shape, np.nan, np.float32)
        HH = np.full(inside.shape, np.nan, np.float32)
        for i, j in zip(*np.nonzero(ok)):
            rr, cc = row[i, j] - r0, col[i, j] - c0
            sl = np.s_[rr - half: rr + half + 1, cc - half: cc + half + 1]
            v = valid[sl]
            if v.sum() >= 0.5 * v.size:
                HV[i, j] = 10 * np.log10(hv[sl][v].mean())
                HH[i, j] = 10 * np.log10(hh[sl][v].mean())
        np.savez_compressed(out, hv_db=HV, hh_db=HH)
        print(slug, d, "células válidas:", int(np.isfinite(HV).sum()), "de", int(inside.sum()), flush=True)


# ---------------------------------------------------------------- montagem
def build() -> None:
    import rasterio

    clima = pd.read_csv(DATA_PROCESSED / "final_5" / "clima_anual_1991_2024.csv")
    index = []
    for slug, p in places().items():
        inside = _inside(p)
        with rasterio.open(WORK / f"{slug}_ndvi.tif") as s:
            ndvi = s.read().astype(np.float32)
        with rasterio.open(WORK / f"{slug}_chuva.tif") as s:
            chuva = s.read().astype(np.float32)
        ndvi[:, ~inside] = np.nan
        chuva[:, ~inside] = np.nan
        ndir = WORK / f"{slug}_nisar"
        files = sorted(ndir.glob("*.npz"))
        dates = [f"{f.stem[:4]}-{f.stem[4:6]}-{f.stem[6:]}" for f in files]
        hv = np.stack([np.load(f)["hv_db"] for f in files]) if files else np.zeros((0, p["h"], p["w"]), np.float32)
        hh = np.stack([np.load(f)["hh_db"] for f in files]) if files else np.zeros((0, p["h"], p["w"]), np.float32)
        np.savez_compressed(PRODUCTS / f"{slug}_ndvi.npz", ndvi=ndvi, chuva=chuva, hv_db=hv, hh_db=hh,
                            anos=np.array(YEARS), west=p["west"], south=p["south"], east=p["east"], north=p["north"],
                            resolution=RES)
        key = f"{p['nome']}/{p['uf']}"
        c = clima[clima.municipio == key].sort_values("ano")
        meta = {"slug": slug, "municipio": p["nome"], "uf": p["uf"],
                "orbita": (ndir / "orbita.txt").read_text() if (ndir / "orbita.txt").exists() else None,
                "datas_nisar": dates,
                "clima_anual": [{"ano": int(r.ano), "chuva_mm": round(float(r.chuva_mm), 1), "temp_c": round(float(r.temp_c), 2)}
                                for r in c.itertuples()],
                "fontes": {"ndvi": "MODIS MOD13Q1 (NDVI anual médio, QA bom)", "chuva": "CHIRPS",
                           "radar": "NISAR L2 GCOV, gamma0 HV/HH em dB", "clima": "CHIRPS e ERA5-Land, média do município"}}
        (PRODUCTS / f"{slug}_ndvi.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        index.append({"slug": slug, "municipio": p["nome"], "uf": p["uf"]})
        print(slug, "ndvi", ndvi.shape, "nisar", hv.shape, "datas", len(dates), flush=True)
    (PRODUCTS / "ndvi_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "nisar":
        nisar(sys.argv[2])
    else:
        {"modis": modis, "build": build}[cmd]()
