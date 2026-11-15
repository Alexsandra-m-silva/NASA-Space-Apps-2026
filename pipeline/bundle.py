"""Monta o pacote leve de resultados que o app carrega (app/bundle/).

O pacote é versionado no git: o compose sobe em qualquer máquina sem credenciais
e sem reprocessar GEE/NISAR. Reprocessar = rodar o pipeline e depois este script.

Uso: python -m pipeline.bundle
"""

from __future__ import annotations

import json
import shutil

import pandas as pd

from pipeline.config import DATA_PROCESSED, ROOT

BUNDLE = ROOT / "app" / "bundle"
FIVE = {"Floresta": "PE", "Currais Novos": "RN", "Parelhas": "RN", "Petrolina": "PE", "Casa Nova": "BA"}
TOL = 0.0015  # ~150 m: simplificação das geometrias para o mapa


def _simplify(features, tol=TOL, keep=None):
    from shapely.geometry import mapping, shape

    out = []
    for f in features:
        g = shape(f["geometry"]).simplify(tol, preserve_topology=True)
        if g.is_empty:
            continue
        props = {k: v for k, v in f["properties"].items() if keep is None or k in keep}
        out.append({"type": "Feature", "properties": props, "geometry": mapping(g)})
    return {"type": "FeatureCollection", "features": out}


def _round_coords(gj, nd=5):
    def r(c):
        return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], nd), round(c[1], nd)]
    for f in gj["features"]:
        f["geometry"]["coordinates"] = r(f["geometry"]["coordinates"])
    return gj


def _write(name, obj):
    (BUNDLE / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    BUNDLE.mkdir(parents=True, exist_ok=True)
    f5 = DATA_PROCESSED / "final_5"
    appd = DATA_PROCESSED / "app"

    aoi = json.loads((DATA_PROCESSED / "poligonos" / "aoi.geojson").read_text(encoding="utf-8"))["features"]
    muns = [f for f in aoi if f["properties"]["municipio"] in FIVE]
    _write("municipios.geojson", _round_coords(_simplify(muns, 0.0005, keep={"municipio", "uf", "ibge"})))

    sus = json.loads((f5 / "suscetibilidade_alta_5municipios.geojson").read_text(encoding="utf-8"))["features"]
    _write("suscetibilidade.geojson", _round_coords(_simplify(sus)))
    deg = json.loads((f5 / "poligonos_modis_5municipios.geojson").read_text(encoding="utf-8"))["features"]
    _write("degradacao_modis.geojson", _round_coords(_simplify(deg, keep={"classe", "municipio", "area_ha"})))

    # resumo por município: MODIS, NISAR, clima, suscetibilidade, SHAP
    modis = pd.read_csv(f5 / "modis_5.csv", index_col=0)
    nisar = pd.read_csv(f5 / "nisar_5.csv", index_col=0)
    clima = pd.read_csv(f5 / "clima_tendencias_5.csv", index_col=0)
    susc = pd.read_csv(f5 / "suscetibilidade_5.csv", index_col=0)
    shap_det = json.loads((appd / "shap_detector_municipios.json").read_text(encoding="utf-8"))
    contrib = json.loads((appd / "contrib_suscetibilidade_municipios.json").read_text(encoding="utf-8"))
    resumo = []
    for nome, uf in FIVE.items():
        key = f"{nome}/{uf}"
        clean = lambda s: {k: (None if pd.isna(v) else (float(v) if isinstance(v, (int, float)) else v)) for k, v in s.items()}
        resumo.append({
            "municipio": nome, "uf": uf, "chave": key,
            "modis": clean(modis.loc[key]) if key in modis.index else None,
            "nisar": clean(nisar.loc[key]) if key in nisar.index else None,
            "clima": clean(clima.loc[key]) if key in clima.index else None,
            "suscetibilidade": clean(susc.loc[key]) if key in susc.index else None,
            "contribuicoes_suscetibilidade": contrib.get(key, {}).get("contribuicoes"),
            "shap_detector": shap_det.get(nome),
        })
    _write("municipios_resumo.json", resumo)

    for m in ("detector", "validador"):
        shutil.copy(appd / f"shap_{m}_global.json", BUNDLE / f"shap_{m}_global.json")
        shutil.copy(appd / f"shap_{m}_beeswarm.png", BUNDLE / f"shap_{m}_beeswarm.png")
    pts = pd.read_csv(appd / "shap_validador_pontos.csv")
    pts = pts[pts.municipio.isin(FIVE)]
    _write("pontos_nisar.geojson", {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r.lon, 5), round(r.lat, 5)]},
         "properties": {"municipio": r.municipio, "prob_degradacao_nisar": round(r.prob, 3)}} for r in pts.itertuples()]})

    meta = {"versao": 1, "municipios": list(FIVE), "fontes": [
        "MODIS MOD13Q1/MOD13A3", "CHIRPS", "ERA5-Land", "MapBiomas Col. 10", "NISAR L2 GCOV (provisório, jun–out/2026)"],
        "metricas": {"validacao_poligonos_auc_14mun": 0.758, "validacao_poligonos_auc_5mun": 0.767,
                     "detector_auc_com_nisar": 0.818, "detector_auc_sem_nisar": 0.717,
                     "suscetibilidade_spearman_nisar": 0.486}}
    _write("meta.json", meta)
    total = sum(p.stat().st_size for p in BUNDLE.iterdir()) / 1e6
    print(f"pacote em {BUNDLE}: {len(list(BUNDLE.iterdir()))} arquivos, {total:.1f} MB")
    for p in sorted(BUNDLE.iterdir()):
        print(f"  {p.name}: {p.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
