"""Polígonos de degradação vegetal (MODIS) e de controle, para validação pelo NISAR.

1. MODIS MOD13Q1 2001–2024 em todos os pixels de 250 m dos 14 municípios.
2. RESTREND por pixel: tendência do NDVI que a chuva CHIRPS não explica (Sen + Mann-Kendall).
   - degradado: tendência negativa, p < 0,05
   - controle:  sem tendência significativa (|tau| pequeno, p > 0,5) e NDVI médio dentro da faixa da Caatinga
   - melhora:   tendência positiva, p < 0,05 (ex.: irrigação nova); é um segundo controle
3. Pixels viram polígonos (mínimo 4 pixels contíguos ≈ 25 ha). Água e urbano (MCD12Q1) ficam fora.
4. Pontos sorteados dentro dos polígonos vão para pipeline.tese (NISAR + XGBoost).

Uso:
    python -m pipeline.poligonos submit     # pede o recorte de área ao AppEEARS
    python -m pipeline.poligonos fetch      # baixa os GeoTIFFs quando prontos
    python -m pipeline.poligonos map REGIAO # RESTREND por pixel + polígonos (serido | sao_francisco)
    python -m pipeline.poligonos sample     # pontos estratificados nos polígonos
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
OUT = DATA_PROCESSED / "poligonos"
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api"
YEARS = list(range(2001, 2025))
MIN_PIXELS = 4


def _token() -> str:
    r = requests.post(f"{APPEEARS}/login", auth=(os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"]), timeout=60)
    r.raise_for_status()
    return r.json()["token"]


def _aoi() -> dict:
    feats = []
    for area in ("serido", "sao_francisco"):
        p = DATA_PROCESSED / f"tese_{area}" / "municipios.geojson"
        if not p.exists():
            from pipeline.tese import municipios_geojson
            feats += municipios_geojson(area)
        else:
            feats += json.loads(p.read_text(encoding="utf-8"))["features"]
    return {"type": "FeatureCollection", "features": feats}


def submit() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    aoi = _aoi()
    (OUT / "aoi.geojson").write_text(json.dumps(aoi, ensure_ascii=False), encoding="utf-8")
    task = {
        "task_type": "area",
        "task_name": "poligonos_degradacao_ndvi",
        "params": {
            "dates": [{"startDate": "01-01-2001", "endDate": "12-31-2024"}],
            "layers": [
                {"product": "MOD13Q1.061", "layer": "_250m_16_days_NDVI"},
                {"product": "MOD13Q1.061", "layer": "_250m_16_days_pixel_reliability"},
                {"product": "MCD12Q1.061", "layer": "LC_Type1"},
            ],
            "output": {"format": {"type": "geotiff"}, "projection": "geographic"},
            "geo": aoi,
        },
    }
    r = requests.post(f"{APPEEARS}/task", json=task, headers={"Authorization": f"Bearer {_token()}"}, timeout=300)
    print(r.status_code, r.text[:300])
    r.raise_for_status()
    (OUT / "appeears_task.json").write_text(r.text, encoding="utf-8")


def fetch() -> None:
    """Baixa os GeoTIFFs de todos os pedidos (por região e período) para tif/<região>/."""
    tasks = json.loads((OUT / "appeears_tasks.json").read_text())
    pending = {t["task_id"]: t for t in tasks}
    while pending:
        headers = {"Authorization": f"Bearer {_token()}"}
        for task_id, t in list(pending.items()):
            st = requests.get(f"{APPEEARS}/task/{task_id}", headers=headers, timeout=60).json()
            print(time.strftime("%H:%M:%S"), t["area"], t["start"], st.get("status"), flush=True)
            if st.get("status") == "error":
                raise SystemExit(st)
            if st.get("status") != "done":
                continue
            tif = OUT / "tif" / t["area"]
            tif.mkdir(parents=True, exist_ok=True)
            files = requests.get(f"{APPEEARS}/bundle/{task_id}", headers=headers, timeout=60).json()["files"]
            for f in files:
                name = f["file_name"].split("/")[-1]
                if name.endswith(".tif") and not (tif / name).exists():
                    data = requests.get(f"{APPEEARS}/bundle/{task_id}/{f['file_id']}", headers=headers, timeout=600)
                    (tif / name).write_bytes(data.content)
            print("baixado", t["area"], t["start"], len(list(tif.glob("*.tif"))), "arquivos", flush=True)
            del pending[task_id]
        if pending:
            time.sleep(300)


# ---------------------------------------------------------------- mapa
def _mann_kendall(y: np.ndarray, t: np.ndarray):
    """Vetorizado por pixel. y: (anos, pixels). Retorna slope de Sen, tau e p (aprox. normal)."""
    from scipy.stats import norm

    n = y.shape[0]
    i, j = np.triu_indices(n, 1)
    diff = y[j] - y[i]                      # (pares, pixels)
    s = np.nansum(np.sign(diff), axis=0)
    valid = np.isfinite(y).sum(axis=0)
    var = valid * (valid - 1) * (2 * valid + 5) / 18.0
    z = np.where(s > 0, (s - 1) / np.sqrt(var), np.where(s < 0, (s + 1) / np.sqrt(var), 0.0))
    p = 2 * (1 - norm.cdf(np.abs(z)))
    slopes = diff / (t[j] - t[i])[:, None]
    sen = np.nanmedian(slopes, axis=0)
    tau = s / (valid * (valid - 1) / 2.0)
    return sen, tau, p


def map_(area: str) -> None:
    import rasterio
    from rasterio.features import shapes, sieve
    from rasterio.warp import Resampling, reproject

    tif = OUT / "tif" / area
    ndvi_files = sorted(tif.glob("*NDVI*.tif"))
    rel_files = {f.name.split("_doy")[1][:7]: f for f in tif.glob("*reliability*.tif")}
    with rasterio.open(ndvi_files[0]) as ref:
        profile, H, W = ref.profile, ref.height, ref.width
        transform, crs = ref.transform, ref.crs

    # NDVI médio anual com qualidade boa (reliability 0 ou 1)
    acc = {y: [np.zeros((H, W)), np.zeros((H, W))] for y in YEARS}
    for f in ndvi_files:
        doy = f.name.split("_doy")[1][:7]
        year = int(doy[:4])
        if year not in acc or doy not in rel_files:
            continue
        with rasterio.open(f) as a, rasterio.open(rel_files[doy]) as b:
            v, r = a.read(1).astype(float), b.read(1)
        ok = np.isin(r, [0, 1]) & (v > -3000)
        v = v * 0.0001 if np.nanmax(v[ok], initial=0) > 2 else v
        acc[year][0][ok] += v[ok]
        acc[year][1][ok] += 1
    ndvi = np.stack([np.where(acc[y][1] > 3, acc[y][0] / np.maximum(acc[y][1], 1), np.nan) for y in YEARS])

    # Chuva anual CHIRPS reamostrada para a grade MODIS
    rain = np.full_like(ndvi, np.nan)
    for k, y in enumerate(YEARS):
        url = f"/vsicurl/https://data.chc.ucsb.edu/products/CHIRPS/v2.0/global_annual/tifs/chirps-v2.0.{y}.tif"
        with rasterio.open(url) as src:
            reproject(rasterio.band(src, 1), rain[k], dst_transform=transform, dst_crs=crs,
                      resampling=Resampling.bilinear, src_nodata=-9999, dst_nodata=np.nan)
    rain[rain < 0] = np.nan

    # RESTREND por pixel
    yflat, rflat = ndvi.reshape(len(YEARS), -1), rain.reshape(len(YEARS), -1)
    ok = np.isfinite(yflat) & np.isfinite(rflat)
    n = ok.sum(0)
    rm = np.where(ok, rflat, 0).sum(0) / np.maximum(n, 1)
    ym = np.where(ok, yflat, 0).sum(0) / np.maximum(n, 1)
    cov = np.where(ok, (rflat - rm) * (yflat - ym), 0).sum(0)
    var = np.where(ok, (rflat - rm) ** 2, 0).sum(0)
    b = cov / np.where(var > 0, var, np.nan)
    resid = np.where(ok, yflat - (ym + b * (rflat - rm)), np.nan)
    sen, tau, p = _mann_kendall(resid, np.asarray(YEARS, float))
    enough = n >= 15

    lc = None
    lc_files = sorted(tif.glob("*LC_Type1*.tif"))
    if lc_files:
        with rasterio.open(lc_files[-1]) as src:
            lc = src.read(1).reshape(-1)
    excluded = np.isin(lc, [13, 17]) if lc is not None else np.zeros_like(enough)
    ndvi_mean = np.nanmean(yflat, axis=0)

    cls = np.zeros(H * W, np.uint8)  # 0 sem dado/excluído
    cls[enough & ~excluded & (sen < 0) & (p < 0.05)] = 1                      # degradado
    cls[enough & ~excluded & (p > 0.5) & (ndvi_mean > 0.25)] = 2               # controle estável
    cls[enough & ~excluded & (sen > 0) & (p < 0.05)] = 3                      # melhora
    cls = cls.reshape(H, W)

    prof = profile | {"count": 1, "dtype": "uint8", "nodata": 0, "compress": "deflate"}
    with rasterio.open(OUT / f"classes_{area}.tif", "w", **prof) as dst:
        dst.write(cls, 1)
    prof_f = profile | {"count": 3, "dtype": "float32", "nodata": np.nan, "compress": "deflate"}
    with rasterio.open(OUT / f"restrend_{area}.tif", "w", **prof_f) as dst:
        dst.write(np.stack([sen, tau, p]).reshape(3, H, W).astype("float32"))

    # Polígonos: só manchas com >= MIN_PIXELS pixels contíguos
    names = {1: "degradado", 2: "controle_estavel", 3: "melhora"}
    feats = []
    for code, name in names.items():
        mask = (cls == code).astype(np.uint8)
        mask = sieve(mask, size=MIN_PIXELS, connectivity=8)
        for geom, val in shapes(mask, mask=mask.astype(bool), transform=transform, connectivity=8):
            feats.append({"type": "Feature", "properties": {"classe": name, "regiao": area}, "geometry": geom})
    gj = {"type": "FeatureCollection", "features": feats}
    (OUT / f"poligonos_{area}.geojson").write_text(json.dumps(gj), encoding="utf-8")
    px_km2 = abs(transform.a * transform.e) * (111.32 ** 2)
    summary = {names[c]: {"pixels": int((cls == c).sum()), "km2_aprox": round(float((cls == c).sum() * px_km2), 1),
                          "poligonos": sum(f["properties"]["classe"] == names[c] for f in feats)} for c in names}
    (OUT / f"resumo_{area}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- mapa via Google Earth Engine
MAPBIOMAS10 = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_integration_v2"
MB_EXCLUDE = [24, 30, 31, 33]  # urbano, mineração, aquicultura, água
MB_IRRIGATED = [40, 41, 46, 47, 48, 62]  # lavouras (arroz, outras temporárias, café, citrus, outras perenes, algodão)


def gee_map(area: str) -> None:
    """Mesmo RESTREND do `map`, calculado no GEE (minutos em vez de horas no AppEEARS)."""
    import ee
    import rasterio
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

    ee.Initialize(project=os.environ["GEE_PROJECT"])
    feats = [f for f in json.loads((OUT / "aoi.geojson").read_text(encoding="utf-8"))["features"]
             if f["properties"]["area"] == area]
    geom = unary_union([shape(f["geometry"]) for f in feats]).buffer(0.003)
    region = ee.Geometry(mapping(geom))

    def annual(y):
        y = ee.Number(y)
        s = ee.Date.fromYMD(y, 1, 1)
        e = s.advance(1, "year")
        ndvi = (ee.ImageCollection("MODIS/061/MOD13Q1").filterDate(s, e)
                .map(lambda i: i.select("NDVI").multiply(0.0001).updateMask(i.select("SummaryQA").lte(1)))
                .mean().rename("ndvi"))
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum().rename("rain")
        return ndvi.addBands(rain).addBands(ee.Image.constant(y).toFloat().rename("t"))

    stack = ee.ImageCollection(ee.List(YEARS).map(annual))
    fit = stack.select(["rain", "ndvi"]).reduce(ee.Reducer.linearFit())
    res = stack.map(lambda i: i.select("ndvi").subtract(fit.select("offset").add(fit.select("scale").multiply(i.select("rain"))))
                    .rename("resid").addBands(i.select("t")))
    sen = res.select(["t", "resid"]).reduce(ee.Reducer.sensSlope()).select("slope").rename("sen")
    mk = res.select(["t", "resid"]).reduce(ee.Reducer.kendallsCorrelation(2))
    n = stack.select("ndvi").count().rename("n")
    ndvi_mean = stack.select("ndvi").mean().rename("ndvi_mean")
    # MapBiomas 30 m: a exportação a 250 m usa a pirâmide de MODA do asset (classe categórica).
    mb250 = ee.Image(MAPBIOMAS10).select("classification_2024").rename("lc")
    excl = mb250.remap(MB_EXCLUDE, [1] * len(MB_EXCLUDE), 0)
    base = n.gte(15).And(excl.Not())
    # Mann-Kendall pela variância de tau (sem empates): var = 2(2n+5) / (9n(n-1)); z = tau / sd.
    # A banda "p-value" do reducer veio zerada nos testes, por isso o z é calculado aqui.
    tau = mk.select("tau")
    nn = res.select("resid").count()
    sd = nn.multiply(2).add(5).multiply(2).divide(nn.multiply(nn.subtract(1)).multiply(9)).sqrt()
    z = tau.divide(sd).abs()
    sig = z.gt(1.96)      # p < 0,05
    flat = z.lt(0.674)    # p > 0,5
    cls = (ee.Image(0)
           .where(base.And(sen.lt(0)).And(sig), 1)
           .where(base.And(flat).And(ndvi_mean.gt(0.25)), 2)
           .where(base.And(sen.gt(0)).And(sig), 3)
           .rename("cls").toByte())
    stats = cls.reduceRegion(ee.Reducer.frequencyHistogram(), region, scale=250, maxPixels=1e9).getInfo()
    print(area, "pixels por classe (GEE):", stats)
    out = (cls.addBands(sen.multiply(1e5).toInt16()).addBands(tau.multiply(1e4).toInt16())
           .addBands(ndvi_mean.multiply(1e4).toInt16()).addBands(mb250.toByte().toInt16())).clip(region)

    url = out.getDownloadURL({"region": region, "scale": 250, "crs": "EPSG:4326", "format": "GEO_TIFF",
                              "filePerBand": False})
    tif = OUT / f"gee_{area}.tif"
    tif.write_bytes(requests.get(url, timeout=600).content)
    with rasterio.open(tif) as src:
        arr, transform, profile = src.read(), src.transform, src.profile
    cls_arr = arr[0].astype(np.uint8)
    polygonize(area, cls_arr, transform, profile)


def polygonize(area: str, cls, transform, profile) -> None:
    import rasterio
    from rasterio.features import shapes, sieve

    prof = profile | {"count": 1, "dtype": "uint8", "nodata": 0, "compress": "deflate"}
    with rasterio.open(OUT / f"classes_{area}.tif", "w", **prof) as dst:
        dst.write(cls, 1)
    names = {1: "degradado", 2: "controle_estavel", 3: "melhora"}
    feats = []
    for code, name in names.items():
        mask = sieve((cls == code).astype(np.uint8), size=MIN_PIXELS, connectivity=8)
        for geom, _ in shapes(mask, mask=mask.astype(bool), transform=transform, connectivity=8):
            feats.append({"type": "Feature", "properties": {"classe": name, "regiao": area}, "geometry": geom})
    (OUT / f"poligonos_{area}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    px_km2 = abs(transform.a * transform.e) * (111.32 ** 2)
    summary = {names[c]: {"pixels": int((cls == c).sum()), "km2_aprox": round(float((cls == c).sum() * px_km2), 1),
                          "poligonos": sum(f["properties"]["classe"] == names[c] for f in feats)} for c in names}
    (OUT / f"resumo_{area}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(area, json.dumps(summary, ensure_ascii=False))


def sample(per_class: int = 1200) -> None:
    """Pontos no centro de pixels de cada classe, já no formato de pipeline.tese."""
    import rasterio
    from shapely.geometry import Point, shape

    from rasterio.features import sieve
    rng = np.random.default_rng(7)
    aoi = [(f["properties"]["municipio"], f["properties"]["area"], shape(f["geometry"]))
           for f in json.loads((OUT / "aoi.geojson").read_text(encoding="utf-8"))["features"]]
    rows = []
    for area in ("serido", "sao_francisco"):
      with rasterio.open(OUT / f"classes_{area}.tif") as src:
        cls, transform = src.read(1), src.transform
      for code, name in {1: "degradado", 2: "controle_estavel", 3: "melhora"}.items():
        m = sieve((cls == code).astype(np.uint8), size=MIN_PIXELS, connectivity=8).astype(bool)
        rr, cc = np.nonzero(m)
        take = rng.choice(len(rr), size=min(per_class // 2, len(rr)), replace=False)
        for k in take:
            x, y = transform * (cc[k] + 0.5, rr[k] + 0.5)
            mun = next((n for n, a, g in aoi if g.contains(Point(x, y))), None)
            if mun is None:  # buffer do recorte AppEEARS
                continue
            rows.append({"classe": name, "lon": round(x, 6), "lat": round(y, 6), "municipio": mun, "regiao": area})
    df = pd.DataFrame(rows)
    df.insert(0, "id", range(len(df)))
    d = DATA_PROCESSED / "tese_poligonos"
    d.mkdir(parents=True, exist_ok=True)
    df.to_csv(d / "points.csv", index=False)
    print(df.groupby(["regiao", "classe"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "map":
        map_(sys.argv[2])
    elif cmd == "gee":
        gee_map(sys.argv[2])
    else:
        {"submit": submit, "fetch": fetch, "sample": sample}[cmd]()
