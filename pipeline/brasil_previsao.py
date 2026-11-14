"""Tendência de degradação da vegetação no Brasil, 12 meses à frente (1 km).

Adaptação do modelo do Simemap (parceria_simemap/backend/analytics/energy_forecast.py):
- série mensal regular, faltas continuam ausentes;
- features só com informação até a origem (lags >= horizonte, médias móveis deslocadas);
- "sinal" de um modelo de série temporal (tendência linear das anomalias dos últimos 10 anos,
  extrapolada ao horizonte; papel do SARIMAX no Simemap) entra como feature do gradient boosting;
- combinação convexa sinal/boosting com peso escolhido só na validação;
- avaliação walk-forward por origem, contra modelos ingênuos.

Série alvo: NDVI MODIS mensal (MOD13A3, 1 km), anomalia em relação à climatologia mensal 2001–2020.
Origem: fim de outubro de cada ano. Alvo: anomalia média de novembro a outubro seguinte (12 meses).
Variáveis externas: chuva (CHIRPS), temperatura e umidade do solo (ERA5-Land), aridez, uso do solo (MapBiomas).
O NISAR NÃO entra no mapa nacional (sem cobertura processada); é validado regionalmente (ver final_5/).

Uso:
    python -m pipeline.brasil_previsao sample     # pontos x origens -> CSV
    python -m pipeline.brasil_previsao validate   # walk-forward local (XGBoost, como no Simemap)
    python -m pipeline.brasil_previsao export     # treina GBT no GEE e exporta a previsão 2026->2027 (asset)
    python -m pipeline.brasil_previsao download   # baixa o asset em tiles e monta o GeoTIFF
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
OUT = DATA_PROCESSED / "brasil"
ORIGINS = list(range(2011, 2026))   # alvo da última origem: nov/2025–out/2026
FORECAST_ORIGIN = 2026              # previsão nov/2026–out/2027
SCALE = 1000
MB = "projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_integration_v2"
NATIVE = [3, 4, 5, 6, 11, 12, 13, 49, 50]
FEATURES = ["anom_3m", "anom_12m", "anom_lag12", "anom_lag24", "tend_10a", "sinal_tendencia",
            "chuva_anom_3m", "chuva_anom_12m", "temp_anom_12m", "umid_anom_12m", "aridez", "ndvi_clima", "nativa", "lc"]
ASSET_DIR = None  # definido em _asset_dir()


# ---------------------------------------------------------------- GEE: séries mensais e features
def _ee():
    import ee
    ee.Initialize(project=os.environ["GEE_PROJECT"])
    return ee


def _collections(ee):
    """Coleções mensais de anomalias (NDVI, chuva, temperatura, umidade do solo)."""
    ndvi = (ee.ImageCollection("MODIS/061/MOD13A3")
            .map(lambda i: i.select("NDVI").multiply(0.0001).updateMask(i.select("SummaryQA").lte(1))
                 .rename("v").copyProperties(i, ["system:time_start"])))
    chirps_p = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD")
    n_months = (2026 - 2001) * 12 + 10
    starts = ee.List.sequence(0, n_months - 1).map(lambda k: ee.Date("2001-01-01").advance(k, "month").millis())

    def chirps_month(ms):
        d = ee.Date(ms)
        c = chirps_p.filterDate(d, d.advance(1, "month"))
        return ee.Image(ee.Algorithms.If(c.size().gte(5), c.sum(), ee.Image().float().selfMask())).rename("v") \
            .set("system:time_start", ms)
    rain = ee.ImageCollection(starts.map(chirps_month))
    era = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
    temp = era.map(lambda i: i.select("temperature_2m").subtract(273.15).rename("v").copyProperties(i, ["system:time_start"]))
    soil = era.map(lambda i: i.select("volumetric_soil_water_layer_1").rename("v").copyProperties(i, ["system:time_start"]))
    pet = era.map(lambda i: i.select("potential_evaporation_sum").multiply(-1000).rename("v").copyProperties(i, ["system:time_start"]))

    def anomalies(col):
        base = col.filterDate("2001-01-01", "2021-01-01")
        clim = ee.List.sequence(1, 12).map(lambda m: base.filter(ee.Filter.calendarRange(m, m, "month")).mean())

        def an(i):
            m = ee.Date(i.get("system:time_start")).get("month")
            return i.subtract(ee.Image(clim.get(ee.Number(m).subtract(1)))).rename("v") \
                .copyProperties(i, ["system:time_start"])
        return col.map(an), clim
    ndvi_a, ndvi_clim = anomalies(ndvi)
    rain_a, _ = anomalies(rain)
    temp_a, _ = anomalies(temp)
    soil_a, _ = anomalies(soil)
    aridez = rain.filterDate("2001-01-01", "2021-01-01").sum().divide(pet.filterDate("2001-01-01", "2021-01-01").sum()).rename("aridez")
    ndvi_clima = ee.ImageCollection(ndvi_clim).mean().rename("ndvi_clima")
    return ndvi_a, rain_a, temp_a, soil_a, aridez, ndvi_clima


def _features(ee, cols, year):
    """Imagem de features na origem (fim de outubro de `year`) e alvo (nov/year–out/year+1)."""
    ndvi_a, rain_a, temp_a, soil_a, aridez, ndvi_clima = cols
    o = ee.Date.fromYMD(year, 11, 1)  # primeiro dia depois da origem
    win = lambda col, m0, m1: col.filterDate(o.advance(m0, "month"), o.advance(m1, "month")).mean()
    hist = ndvi_a.filterDate(o.advance(-120, "month"), o).map(
        lambda i: i.addBands(ee.Image.constant(ee.Date(i.get("system:time_start")).difference(o, "year")).toFloat().rename("t"))
        .select(["t", "v"]))
    fit = hist.reduce(ee.Reducer.linearFit())  # anomalia ~ a + b*t ; t = anos antes da origem (negativo)
    sinal = fit.select("offset").add(fit.select("scale").multiply(0.5))  # média do horizonte (t de 0 a 1 ano)
    lc_year = min(year, 2024)
    lc = ee.Image(MB).select(f"classification_{lc_year}").unmask(0)
    img = ee.Image.cat([
        win(ndvi_a, -3, 0).rename("anom_3m"),
        win(ndvi_a, -12, 0).rename("anom_12m"),
        win(ndvi_a, -24, -12).rename("anom_lag12"),
        win(ndvi_a, -36, -24).rename("anom_lag24"),
        fit.select("scale").multiply(10).rename("tend_10a"),
        sinal.rename("sinal_tendencia"),
        win(rain_a, -3, 0).rename("chuva_anom_3m"),
        win(rain_a, -12, 0).rename("chuva_anom_12m"),
        win(temp_a, -12, 0).rename("temp_anom_12m"),
        win(soil_a, -12, 0).rename("umid_anom_12m"),
        aridez, ndvi_clima,
        lc.remap(NATIVE, [1] * len(NATIVE), 0).rename("nativa"),
        lc.rename("lc"),
    ]).toFloat()
    target = win(ndvi_a, 0, 12).rename("alvo")
    return img, target


def _brazil(ee):
    return ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017").filter(ee.Filter.eq("country_na", "Brazil")).geometry()


def _points(ee, n_brasil=5000, n_seco=2500, seed=42):
    br = _brazil(ee)
    cols = _collections(ee)
    seco = cols[4].lt(0.65).selfMask().reduceToVectors(geometry=br, scale=20000, maxPixels=1e10, geometryType="polygon")
    p1 = ee.FeatureCollection.randomPoints(br, n_brasil, seed)
    p2 = ee.FeatureCollection.randomPoints(seco.geometry(), n_seco, seed + 1)
    return p1.merge(p2), cols


def sample() -> None:
    ee = _ee()
    OUT.mkdir(parents=True, exist_ok=True)
    pts, cols = _points(ee)
    coords = pts.geometry().coordinates().getInfo()
    P = pd.DataFrame(coords, columns=["lon", "lat"])
    P["pid"] = range(len(P))
    P.to_csv(OUT / "pontos.csv", index=False)
    print("pontos:", len(P), flush=True)
    frames = []
    for year in ORIGINS:
        cache = OUT / f"amostra_{year}.csv"
        if cache.exists():
            frames.append(pd.read_csv(cache))
            continue
        img, target = _features(ee, cols, year)
        stack = img.addBands(target)
        rows = []
        for k in range(0, len(P), 1500):
            chunk = P.iloc[k:k + 1500]
            fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"pid": int(r.pid)}) for r in chunk.itertuples()])
            for attempt in range(3):
                try:
                    res = stack.reduceRegions(fc, ee.Reducer.first(), scale=SCALE, tileScale=8).getInfo()["features"]
                    break
                except Exception as e:
                    print("  tentativa", attempt + 1, str(e)[:120], flush=True)
                    time.sleep(10)
            rows += [f["properties"] for f in res]
        df = pd.DataFrame(rows)
        df["origem"] = year
        df.to_csv(cache, index=False)
        frames.append(df)
        print(year, len(df), flush=True)
    pd.concat(frames).to_csv(OUT / "amostra.csv", index=False)


# ---------------------------------------------------------------- validação walk-forward (local)
def validate() -> None:
    from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score
    from xgboost import XGBRegressor

    d = pd.read_csv(OUT / "amostra.csv").dropna(subset=["alvo", "anom_12m", "sinal_tendencia"])
    P = pd.read_csv(OUT / "pontos.csv")
    d = d.merge(P, on="pid")
    d["seco"] = d.aridez < 0.65
    feats_xgb = [f for f in FEATURES if f != "sinal_tendencia"]
    feats_hib = FEATURES

    def fit(tr, cols):
        # pesos maiores para origens recentes (como o decaimento de 14 dias do Simemap)
        w = np.exp(-(tr.origem.max() - tr.origem) / 4.0)
        return XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.04, min_child_weight=12, reg_lambda=10,
                            subsample=0.85, colsample_bytree=0.9, tree_method="hist", random_state=42,
                            n_jobs=4).fit(tr[cols], tr.alvo, sample_weight=w)

    rows, preds = [], []
    test_years = [y for y in ORIGINS if y >= 2017]
    weight_prev = 0.5
    for y in test_years:
        tr = d[d.origem <= y - 1]  # alvo da origem o (nov/o–out/o+1) só está observado na origem y se o + 1 <= y
        te = d[d.origem == y]
        m_x, m_h = fit(tr, feats_xgb), fit(tr, feats_hib)
        p = {"zero (climatologia)": np.zeros(len(te)), "persistência 12m": te.anom_12m.to_numpy(),
             "sinal de tendência": te.sinal_tendencia.to_numpy(), "XGBoost": m_x.predict(te[feats_xgb]),
             "XGBoost + sinal (híbrido)": m_h.predict(te[feats_hib])}
        # peso da combinação escolhido na origem anterior (validação), aplicado nesta
        p["combinação híbrido/sinal"] = weight_prev * p["XGBoost + sinal (híbrido)"] + (1 - weight_prev) * p["sinal de tendência"]
        cand = [(mean_absolute_error(te.alvo, w * p["XGBoost + sinal (híbrido)"] + (1 - w) * p["sinal de tendência"]),
                 abs(w - .5), w) for w in np.linspace(0, 1, 11)]
        weight_prev = min(cand)[2]
        queda = (te.alvo < -0.02).astype(int)
        for name, pr in p.items():
            for sub, mask in [("Brasil", np.ones(len(te), bool)), ("terras secas", te.seco.to_numpy())]:
                if mask.sum() < 50:
                    continue
                a, b, q = te.alvo.to_numpy()[mask], pr[mask], queda.to_numpy()[mask]
                rows.append({"origem": y, "modelo": name, "recorte": sub, "MAE": mean_absolute_error(a, b),
                             "R2": r2_score(a, b), "AUC_queda": roc_auc_score(q, -b) if 0 < q.mean() < 1 else np.nan})
        preds.append(te.assign(pred=p["XGBoost + sinal (híbrido)"]))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "validacao_walkforward.csv", index=False)
    S = R.groupby(["recorte", "modelo"])[["MAE", "R2", "AUC_queda"]].mean().round(4)
    imp = pd.Series(fit(d[d.origem <= ORIGINS[-1]], feats_hib).feature_importances_, index=feats_hib).sort_values(ascending=False)
    L = ["# Previsão 12 meses — validação walk-forward (Brasil, MODIS mensal 1 km)", "",
         f"Pontos: {d.pid.nunique()} · origens de teste: {test_years[0]}–{test_years[-1]} (cada uma treinada só com o passado).",
         "Alvo: anomalia média do NDVI nos 12 meses seguintes à origem (out). Queda = anomalia < −0,02.", "",
         S.to_markdown(), "", "## Importância das features (híbrido, ganho)", "", imp.round(3).to_frame("importância").to_markdown()]
    (OUT / "validacao.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


# ---------------------------------------------------------------- produção no GEE
def _asset_dir(ee):
    root = f"projects/{os.environ['GEE_PROJECT']}/assets/nasa_desertificacao"
    try:
        ee.data.getAsset(root)
    except Exception:
        ee.data.createAsset({"type": "FOLDER"}, root)
    return root


def export() -> None:
    ee = _ee()
    root = _asset_dir(ee)
    cols = _collections(ee)
    P = pd.read_csv(OUT / "pontos.csv")
    d = pd.read_csv(OUT / "amostra.csv").dropna(subset=["alvo"] + FEATURES)
    d = d[d.origem >= 2013].merge(P, on="pid")
    d = d.sample(min(len(d), 60000), random_state=1)
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {**{f: float(getattr(r, f)) for f in FEATURES},
                                                                              "alvo": float(r.alvo)}) for r in d.itertuples()])
    gbt = (ee.Classifier.smileGradientTreeBoost(numberOfTrees=200, shrinkage=0.04, samplingRate=0.85, maxNodes=8,
                                                loss="LeastSquares", seed=42)
           .setOutputMode("REGRESSION").train(fc, "alvo", FEATURES))
    img, _ = _features(ee, cols, FORECAST_ORIGIN)
    pred = img.classify(gbt).rename("previsao")
    sinal = img.select("sinal_tendencia")
    tend = img.select("tend_10a")
    seco = img.select("aridez").lt(0.65)
    # classe: 3 queda prevista e tendência de queda em terra seca; 2 um dos dois em terra seca;
    #         1 estável; 0 melhora prevista
    queda, tqueda = pred.lt(-0.02), tend.lt(-0.01)
    classe = (ee.Image(1).where(pred.gt(0.02), 0)
              .where(seco.And(queda.Or(tqueda)), 2).where(seco.And(queda).And(tqueda), 3).rename("classe"))
    out = ee.Image.cat([pred.multiply(1e4).toInt16(), tend.multiply(1e4).toInt16().rename("tend_10a"),
                        sinal.multiply(1e4).toInt16().rename("sinal"), img.select("aridez").multiply(1e3).toInt16(),
                        classe.toInt16()]).clip(_brazil(ee))
    asset = f"{root}/previsao_ndvi_{FORECAST_ORIGIN}_{FORECAST_ORIGIN + 1}"
    try:
        ee.data.deleteAsset(asset)
    except Exception:
        pass
    task = ee.batch.Export.image.toAsset(image=out, description="previsao_brasil_12m", assetId=asset,
                                         region=_brazil(ee).bounds(), scale=SCALE, crs="EPSG:4326", maxPixels=1e10)
    task.start()
    json.dump({"asset": asset, "task": task.id}, open(OUT / "export_task.json", "w"))
    print("export iniciado", task.id, asset)
    while task.active():
        time.sleep(30)
        print(time.strftime("%H:%M:%S"), task.status()["state"], flush=True)
    print(task.status())


def download() -> None:
    import rasterio
    from rasterio.merge import merge

    ee = _ee()
    asset = json.load(open(OUT / "export_task.json"))["asset"]
    img = ee.Image(asset)
    tiles = OUT / "tiles"
    tiles.mkdir(exist_ok=True)
    br = _brazil(ee)
    for x in range(-74, -34, 4):
        for y in range(-34, 6, 4):
            out = tiles / f"t_{x}_{y}.tif"
            if out.exists():
                continue
            box = ee.Geometry.Rectangle([x, y, x + 4, y + 4])
            if not box.intersects(br, 1000).getInfo():
                continue
            url = img.getDownloadURL({"region": box, "scale": SCALE, "crs": "EPSG:4326", "format": "GEO_TIFF"})
            r = requests.get(url, timeout=600)
            if r.content[:2] in (b"II", b"MM"):
                out.write_bytes(r.content)
            else:
                print("falhou", out.name, r.text[:200])
    srcs = [rasterio.open(p) for p in sorted(tiles.glob("*.tif"))]
    mosaic, transform = merge(srcs, nodata=-32768)
    prof = srcs[0].profile | {"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": transform,
                              "compress": "deflate", "nodata": -32768, "count": mosaic.shape[0]}
    for s in srcs:
        s.close()
    dst_path = OUT / f"tendencia_degradacao_brasil_{FORECAST_ORIGIN}_{FORECAST_ORIGIN + 1}.tif"
    with rasterio.open(dst_path, "w", **prof) as dst:
        dst.write(mosaic)
        for i, name in enumerate(["previsao_anom_ndvi_x1e4", "tendencia_10a_x1e4", "sinal_x1e4", "aridez_x1e3",
                                  "classe(0 melhora,1 estavel,2 atencao,3 alerta)"], 1):
            dst.set_band_description(i, name)
    cls = mosaic[4]
    valid = cls != -32768
    print(dst_path, {k: f"{100 * (cls[valid] == k).mean():.1f}%" for k in (0, 1, 2, 3)})


if __name__ == "__main__":
    {"sample": sample, "validate": validate, "export": export, "download": download}[sys.argv[1]]()
