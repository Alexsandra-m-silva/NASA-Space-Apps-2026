"""Territórios reais para o frontend Climate Sentinel (substitui o mockup de platform/).

Gera, no formato `Territory` de platform/src/data/explore/types.ts, os 18 municípios analisados,
os agregados por estado e o agregado da Caatinga (só dos municípios analisados).

Cada campo tem fonte em `fontes`; os dois sem dado observado são ESTIMATIVAS rotuladas:
  custoPrevenirMi        área degradada × custo de condução da regeneração natural na Caatinga em condição
                         desfavorável (TNC 2018, tab. 11: R$ 10.955/ha, corrigido pelo IPCA)
  creditosCarbonoTco2e   área degradada × 14,7 t C/ha de carbono do solo perdidos na conversão de Caatinga densa
                         em pastagem degradada (Bieluczyk et al., J. Environ. Manage.) × 44/12

Saídas: app/bundle/territorios.json e platform/src/data/explore/territories.generated.json
Uso: python -m pipeline.territorios
"""

from __future__ import annotations

import json
import os
import urllib.request

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from pipeline.config import DATA_PROCESSED, ROOT

load_dotenv(ROOT / ".env")
WORK = DATA_PROCESSED / "territorios"
UF_NAMES = {"PE": "Pernambuco", "BA": "Bahia", "RN": "Rio Grande do Norte", "PI": "Piauí", "CE": "Ceará", "PB": "Paraíba"}
AREA_NAMES = {"serido": "Seridó núcleo (RN)", "sao_francisco": "Sub-middle São Francisco (PE/BA)",
              "comprovados": "Official desertification cores (PI/CE/PE)"}
HYDRO = [12100, 12200, 12300, 13214]
DROUGHT = [14110, 14120]
RESTORE_BRL_HA_2018 = 10955.0         # TNC 2018, tabela 11, Cond.RN, condição desfavorável (Caatinga)
SOIL_C_T_HA = 14.7                     # Bieluczyk et al., J. Environ. Manage. (via Agência FAPESP, 2025)
TCO2E_PER_HA = SOIL_C_T_HA * 44 / 12
SOURCES = {
    "tendenciaPp": "MODIS MOD13Q1 NDVI 2001–2024 with rainfall removed (CHIRPS, RESTREND, Mann-Kendall p<0.05): % of the municipality area with declining vegetation",
    "risk": "Thresholds on the MODIS declining-vegetation share: ≥8% critical, ≥3% high, otherwise moderate (consistent with the susceptibility index where it exists)",
    "impacts": "Rules on observed data: water deficit = significant warming or drier aridity (CHIRPS/ERA5-Land 1991–2024); income loss = drought losses recorded in Atlas Digital 2015–2024; migration/emergency = recognised drought or flood emergencies 2015–2024 (Atlas); biodiversity = native-vegetation loss (MapBiomas/MODIS)",
    "custoNaoAgirMi": "Observed: economic losses from droughts and floods recorded in the Atlas Digital de Desastres 2015–2024 (S2iD), inflation-adjusted (IPCA)",
    "custoPrevenirMi": "ESTIMATE: degraded area × R$ 10,955/ha (assisted natural regeneration in the Caatinga under unfavourable conditions, TNC 2018, table 11), IPCA-adjusted",
    "populacaoEstimada": "IBGE Census 2022",
    "areaRecuperavelHa": "Degraded area mapped by MODIS (hectares)",
    "creditosCarbonoTco2e": "ESTIMATE: degraded area × 53.9 tCO2e/ha (14.7 t C/ha soil carbon lost when dense Caatinga becomes degraded pasture, Bieluczyk et al., J. Environ. Manage.)",
    "regeneracaoStatus": "MODIS: improving area > declining area → regenerating; otherwise → to restore",
}


def _ee():
    import ee
    ee.Initialize(project=os.environ["GEE_PROJECT"])
    return ee


def _aoi():
    return json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))["features"]


def _cached(name: str, fn):
    path = WORK / name
    if path.exists():
        return pd.read_csv(path)
    df = fn()
    WORK.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


# ---------------------------------------------------------------- MODIS (mesma classificação do pipeline.poligonos)
def modis_stats() -> pd.DataFrame:
    ee = _ee()
    from pipeline.poligonos import MAPBIOMAS10, MB_EXCLUDE, YEARS

    def annual(y):
        y = ee.Number(y)
        s = ee.Date.fromYMD(y, 1, 1)
        e = s.advance(1, "year")
        ndvi = (ee.ImageCollection("MODIS/061/MOD13Q1").filterDate(s, e)
                .map(lambda i: i.select("NDVI").multiply(0.0001).updateMask(i.select("SummaryQA").lte(1))).mean().rename("ndvi"))
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum().rename("rain")
        return ndvi.addBands(rain).addBands(ee.Image.constant(y).toFloat().rename("t"))

    stack = ee.ImageCollection(ee.List(YEARS).map(annual))
    fit = stack.select(["rain", "ndvi"]).reduce(ee.Reducer.linearFit())
    res = stack.map(lambda i: i.select("ndvi").subtract(fit.select("offset").add(fit.select("scale").multiply(i.select("rain"))))
                    .rename("resid").addBands(i.select("t")))
    sen = res.select(["t", "resid"]).reduce(ee.Reducer.sensSlope()).select("slope")
    tau = res.select(["t", "resid"]).reduce(ee.Reducer.kendallsCorrelation(2)).select("tau")
    n = res.select("resid").count()
    z = tau.divide(n.multiply(2).add(5).multiply(2).divide(n.multiply(n.subtract(1)).multiply(9)).sqrt()).abs()
    excl = ee.Image(MAPBIOMAS10).select("classification_2024").remap(MB_EXCLUDE, [1] * len(MB_EXCLUDE), 0)
    base = n.gte(15).And(excl.Not())
    cls = (ee.Image(0).where(base.And(sen.lt(0)).And(z.gt(1.96)), 1).where(base.And(z.lt(0.674)), 2)
           .where(base.And(sen.gt(0)).And(z.gt(1.96)), 3).rename("cls"))
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry(f["geometry"]), {"ibge": f["properties"]["ibge"]}) for f in _aoi()])
    out = cls.reduceRegions(fc, ee.Reducer.frequencyHistogram(), scale=250, tileScale=4).getInfo()["features"]
    rows = []
    for f in out:
        h = {int(float(k)): v for k, v in (f["properties"].get("histogram") or {}).items()}
        tot = sum(h.values()) or 1
        px_ha = 250 * 250 / 1e4
        rows.append({"ibge": f["properties"]["ibge"], "pct_degradado": 100 * h.get(1, 0) / tot,
                     "pct_estavel": 100 * h.get(2, 0) / tot, "pct_melhora": 100 * h.get(3, 0) / tot,
                     "ha_degradado": h.get(1, 0) * px_ha, "ha_melhora": h.get(3, 0) * px_ha, "ha_total": tot * px_ha})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- clima 1991–2024
def clima_stats() -> pd.DataFrame:
    ee = _ee()
    from scipy.stats import kendalltau, theilslopes

    fc = ee.FeatureCollection([ee.Feature(ee.Geometry(f["geometry"]), {"ibge": f["properties"]["ibge"]}) for f in _aoi()])
    era = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
    rows = []
    for y in range(1991, 2025):
        s, e = f"{y}-01-01", f"{y + 1}-01-01"
        img = (ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum().rename("chuva")
               .addBands(era.filterDate(s, e).select("temperature_2m").mean().subtract(273.15).rename("temp"))
               .addBands(era.filterDate(s, e).select("potential_evaporation_sum").sum().multiply(-1000).rename("etp")))
        for f in img.reduceRegions(fc, ee.Reducer.mean(), scale=5000).getInfo()["features"]:
            rows.append({"ibge": f["properties"]["ibge"], "ano": y, **{k: f["properties"].get(k) for k in ("chuva", "temp", "etp")}})
    d = pd.DataFrame(rows)
    d["aridez"] = d.chuva / d.etp
    out = []
    for ibge, g in d.groupby("ibge"):
        out.append({"ibge": ibge,
                    "temp_tend_decada": theilslopes(g.temp, g.ano)[0] * 10, "temp_p": kendalltau(g.ano, g.temp).pvalue,
                    "aridez_tend_decada": theilslopes(g.aridez, g.ano)[0] * 10, "aridez_p": kendalltau(g.ano, g.aridez).pvalue,
                    "chuva_1991_2007": g[g.ano <= 2007].chuva.mean(), "chuva_2008_2024": g[g.ano >= 2008].chuva.mean()})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- Atlas (prejuízos) e IBGE (população)
def atlas_stats() -> pd.DataFrame:
    from pipeline.atlas_pareto import ipca_factors, load_atlas

    df = load_atlas()
    df["Cod_Cobrade"] = pd.to_numeric(df["Cod_Cobrade"], errors="coerce")
    df["ibge"] = pd.to_numeric(df["Cod_IBGE_Mun"], errors="coerce").astype("Int64").astype(str)
    ibges = {f["properties"]["ibge"] for f in _aoi()}
    df = df[df.ibge.isin(ibges) & df.Cod_Cobrade.isin(HYDRO + DROUGHT)].copy()
    df["data"] = pd.to_datetime(df["Data_Evento"], errors="coerce")
    factors, _ = ipca_factors()
    df["fator"] = df.data.dt.to_period("M").map(factors)
    for c in ("DM_total_danos_materiais", "PE_PLePR"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["perda"] = ((df.DM_total_danos_materiais + df.PE_PLePR) * df.fator).where(df.data >= "1994-07-01", 0).fillna(0)
    rec = df[(df.data >= "2015-01-01") & (df.data < "2025-01-01")]
    out = []
    for ibge in ibges:
        r, a = rec[rec.ibge == ibge], df[df.ibge == ibge]
        out.append({"ibge": ibge, "perda_10a_mi": r.perda.sum() / 1e6, "perda_seca_10a_mi": r[r.Cod_Cobrade.isin(DROUGHT)].perda.sum() / 1e6,
                    "emergencias_10a": int((r.Status.astype(str).str.startswith("Reconhec")).sum()),
                    "eventos_10a": len(r), "perda_1995_2025_mi": a.perda.sum() / 1e6})
    return pd.DataFrame(out)


def populacao() -> pd.DataFrame:
    rows = []
    for f in _aoi():
        ibge = f["properties"]["ibge"]
        url = f"https://apisidra.ibge.gov.br/values/t/4709/n6/{ibge}/v/93/p/2022"
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read()
        if body[:2] == b"\x1f\x8b":
            import gzip
            body = gzip.decompress(body)
        data = json.loads(body)
        rows.append({"ibge": ibge, "populacao": int(data[1]["V"])})
    return pd.DataFrame(rows)


def ipca_2018_to_now() -> float:
    from pipeline.atlas_pareto import ipca_factors
    factors, _ = ipca_factors()
    return float(factors[pd.Period("2018-12", "M")])


# ---------------------------------------------------------------- montagem
def _risk(pct: float) -> str:
    return "critico" if pct >= 8 else "alto" if pct >= 3 else "moderado"


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    feats = _aoi()
    base = pd.DataFrame([{**{k: f["properties"][k] for k in ("municipio", "uf", "ibge", "area")}} for f in feats])
    base = (base.merge(_cached("modis.csv", modis_stats).astype({"ibge": str}), on="ibge")
                .merge(_cached("clima.csv", clima_stats).astype({"ibge": str}), on="ibge")
                .merge(_cached("atlas.csv", atlas_stats).astype({"ibge": str}), on="ibge")
                .merge(_cached("populacao.csv", populacao).astype({"ibge": str}), on="ibge"))
    # NISAR (validação por polígonos, 14 municípios) e suscetibilidade/SHAP (5 municípios)
    pts = pd.read_csv(DATA_PROCESSED / "tese_resultado" / "poligonos_pontos.csv")
    from sklearn.metrics import roc_auc_score
    nis = {}
    for mun, g in pts.groupby("municipio"):
        y = (g.classe == "degradado").astype(int)
        nis[mun] = {"pontos": int(len(g)), "auc": round(float(roc_auc_score(y, g.prob_nisar)), 3) if y.nunique() == 2 and min(y.sum(), (1 - y).sum()) >= 10 else None,
                    "prob_media": round(float(g.prob_nisar.mean()), 3)}
    susc = pd.read_csv(DATA_PROCESSED / "final_5" / "suscetibilidade_5.csv", index_col=0)
    resumo = {f"{r['municipio']}/{r['uf']}": r for r in json.loads((ROOT / "app" / "bundle" / "municipios_resumo.json").read_text(encoding="utf-8"))}
    evid_path = DATA_PROCESSED / "evidencias" / "resumo_municipios.csv"
    evid = pd.read_csv(evid_path, index_col=0) if evid_path.exists() else pd.DataFrame()
    restore_brl_ha = RESTORE_BRL_HA_2018 * ipca_2018_to_now()

    territories = []
    for r in base.itertuples():
        key = f"{r.municipio}/{r.uf}"
        impacts = []
        if (r.temp_p < 0.05 and r.temp_tend_decada > 0) or (r.aridez_tend_decada < 0 and r.aridez_p < 0.1):
            impacts.append("deficit_hidrico")
        if r.perda_seca_10a_mi >= 1:
            impacts.append("perda_renda")
        if r.emergencias_10a > 0:
            impacts.append("migracao")
        desmat = float(evid.loc[key, "desmatamento"]) if key in evid.index and "desmatamento" in evid else None
        if r.pct_degradado >= 2 or (desmat or 0) > 0.01 * r.ha_total:
            impacts.append("pressao_biodiversidade")
        s = susc.loc[key] if key in susc.index else None
        territories.append({
            "id": f"mun-{r.ibge}", "name": r.municipio, "level": "municipio", "parentId": f"uf-{r.uf.lower()}", "mapKey": r.uf,
            "tendenciaPp": round(r.pct_degradado, 1), "risk": _risk(r.pct_degradado), "impacts": impacts,
            "custoNaoAgirMi": round(r.perda_10a_mi, 1), "custoPrevenirMi": round(r.ha_degradado * restore_brl_ha / 1e6, 1),
            "populacaoEstimada": int(r.populacao), "areaRecuperavelHa": round(r.ha_degradado),
            "creditosCarbonoTco2e": round(r.ha_degradado * TCO2E_PER_HA),
            "regeneracaoStatus": "em_regeneracao" if r.ha_melhora > r.ha_degradado else "a_recuperar",
            "estimativas": ["custoPrevenirMi", "creditosCarbonoTco2e"],
            "dados": {
                "uf": r.uf, "ibge": r.ibge, "area_estudo": AREA_NAMES.get(r.area, r.area),
                "pct_melhora": round(r.pct_melhora, 1), "ha_total": round(r.ha_total),
                "aquecimento_c_decada": round(r.temp_tend_decada, 2), "aquecimento_significativo": bool(r.temp_p < 0.05),
                "chuva_1991_2007_mm": round(r.chuva_1991_2007), "chuva_2008_2024_mm": round(r.chuva_2008_2024),
                "perda_seca_10a_mi": round(r.perda_seca_10a_mi, 1), "perda_1995_2025_mi": round(r.perda_1995_2025_mi, 1),
                "emergencias_reconhecidas_10a": int(r.emergencias_10a),
                "nisar": nis.get(r.municipio), "desmatamento_ha_2001_2024": round(desmat) if desmat is not None else None,
                "suscetibilidade_indice": round(float(s["indice_medio"]), 3) if s is not None else None,
                "shap_detector": (resumo.get(key) or {}).get("shap_detector"),
            },
        })

    def aggregate(tid, name, level, parent, map_key, members):
        ha_tot = sum(m["dados"]["ha_total"] for m in members)
        deg = sum(m["areaRecuperavelHa"] for m in members)
        imp = sorted({i for m in members for i in m["impacts"]})
        pct = 100 * deg / ha_tot if ha_tot else 0
        return {"id": tid, "name": name, "level": level, "parentId": parent, "mapKey": map_key,
                "tendenciaPp": round(pct, 1), "risk": _risk(pct), "impacts": imp,
                "custoNaoAgirMi": round(sum(m["custoNaoAgirMi"] for m in members), 1),
                "custoPrevenirMi": round(sum(m["custoPrevenirMi"] for m in members), 1),
                "populacaoEstimada": sum(m["populacaoEstimada"] for m in members), "areaRecuperavelHa": deg,
                "creditosCarbonoTco2e": sum(m["creditosCarbonoTco2e"] for m in members),
                "regeneracaoStatus": "em_regeneracao" if sum(m["dados"]["pct_melhora"] * m["dados"]["ha_total"] for m in members) / 100 > deg else "a_recuperar",
                "estimativas": ["custoPrevenirMi", "creditosCarbonoTco2e"],
                "dados": {"agregado_de": [m["name"] for m in members],
                          "nota": f"Aggregate of the {len(members)} analysed municipalities only, not the whole {level}"}}

    out = list(territories)
    for uf in sorted({t["dados"]["uf"] for t in territories}):
        members = [t for t in territories if t["dados"]["uf"] == uf]
        out.append(aggregate(f"uf-{uf.lower()}", f"{UF_NAMES[uf]} (analysed municipalities)", "estado", "bioma-caatinga", uf, members))
    for area, label in AREA_NAMES.items():
        members = [t for t, f in zip(territories, feats) if f["properties"]["area"] == area]
        if members:
            out.append(aggregate(f"regiao-{area}", label, "regiao", "bioma-caatinga", "", members))
    out.append(aggregate("bioma-caatinga", "Caatinga (18 analysed municipalities)", "bioma", None, "caatinga", territories))

    payload = {"meta": {"fontes": SOURCES, "custo_restauracao_brl_ha": round(restore_brl_ha),
                        "tco2e_por_ha": round(TCO2E_PER_HA, 1), "municipios": len(territories),
                        "referencias": {
                            "TNC 2018": "Restauração da vegetação nativa no Brasil: caracterização de técnicas e estimativas de custo (The Nature Conservancy), tabela 11",
                            "Bieluczyk et al.": "From overgrazed land to forests: assessing soil health in the Caatinga biome, Journal of Environmental Management",
                            "Atlas Digital": "Atlas Digital de Desastres no Brasil, base consolidada 1991–2025 v1.1 (Sedec/MIDR)"}},
               "territories": out}
    for path in (ROOT / "app" / "bundle" / "territorios.json", ROOT / "platform" / "src" / "data" / "explore" / "territories.generated.json"):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(territories)} municípios + {len(out) - len(territories)} agregados")
    print(pd.DataFrame([{k: t[k] for k in ("name", "level", "tendenciaPp", "risk", "custoNaoAgirMi", "custoPrevenirMi",
                                            "populacaoEstimada", "areaRecuperavelHa", "creditosCarbonoTco2e")} | {"impacts": ",".join(t["impacts"])}
                        for t in out]).to_string(index=False))


if __name__ == "__main__":
    main()
