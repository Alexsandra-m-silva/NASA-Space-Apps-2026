"""Explicação dos modelos com SHAP (TreeExplainer) e pacote integrado para o app.

Modelos explicados:
  detector   XGBoost que detecta Caatinga (2014) degradada/convertida até 2024 a partir de
             histórico até 2014 + clima + NISAR 2026 (ver modelo_previsao.py, AUC 0,82)
  validador  XGBoost só com NISAR que separa polígonos MODIS degradados de controles
             (ver tese.analyze_poligonos, AUC 0,76)
  suscetibilidade  índice aditivo (5 componentes, pesos iguais): contribuição = componente / 5

Saídas em data/processed/app/:
  shap_<modelo>_global.json      importância média |SHAP| por variável e por família
  shap_<modelo>_municipios.json  contribuição média por município (explicação local)
  shap_<modelo>_pontos.csv       SHAP por ponto (para o mapa)
  shap_<modelo>_beeswarm.png     figura para a apresentação

Uso: python -m pipeline.shap_modelos
"""

from __future__ import annotations

import json

import matplotlib
import numpy as np
import pandas as pd

from pipeline.config import DATA_PROCESSED

matplotlib.use("Agg")
OUT = DATA_PROCESSED / "app"
SEED = 42

LABELS = {
    "nisar_hv_db": "NISAR HV (dB)", "nisar_hh_db": "NISAR HH (dB)", "nisar_hvhh_db": "NISAR razão HV/HH",
    "nisar_hv_std_t": "NISAR variação temporal HV", "nisar_hh_std_t": "NISAR variação temporal HH",
    "nisar_hv_slope": "NISAR tendência sazonal HV", "nisar_hh_slope": "NISAR tendência sazonal HH",
    "nisar_hv_tex": "NISAR textura HV", "nisar_hh_tex": "NISAR textura HH",
    "nisar_sens_ndvi": "NISAR sensibilidade ao NDVI", "nisar_sens_umidade": "NISAR sensibilidade à umidade",
    "hist_ndvi_media": "NDVI médio 2001–2014", "hist_ndvi_min": "NDVI mínimo 2001–2014",
    "hist_ndvi_cv": "Variabilidade NDVI 2001–2014", "hist_ndvi_tend": "Tendência NDVI 2001–2014",
    "hist_restrend": "Tendência NDVI sem chuva 2001–2014", "hist_queda_seca_2012": "Queda na seca de 2012",
    "hist_lc_2001_nativa": "Vegetação nativa 2001", "hist_lc_2014_nativa": "Vegetação nativa 2014",
    "hist_lc_2014_pastagem": "Pastagem/mosaico 2014", "hist_desmat_ate_2014": "Desmatado até 2014",
    "hist_vigor_2014": "Vigor de pastagem 2014", "clima_temp_tend": "Aquecimento (°C/década)",
    "clima_chuva_rec_vs_hist": "Chuva 2015–24 vs 2001–14", "clima_aridez_rec": "Aridez 2015–2024",
    "clima_chuva_media": "Chuva média", "modis26_ndvi": "NDVI MODIS 2026",
}


def family(c: str) -> str:
    return {"nisar": "NISAR (radar 2026)", "hist": "Histórico 2001–2014 (MODIS/MapBiomas)",
            "clima": "Clima (CHIRPS/ERA5)", "modis26": "MODIS 2026"}[c.split("_")[0]]


def explain(name: str, df: pd.DataFrame, feats: list[str], target: str, group_col: str = "municipio") -> dict:
    import shap
    import matplotlib.pyplot as plt
    from xgboost import XGBClassifier

    d = df.dropna(subset=[target]).reset_index(drop=True)
    X, y = d[feats].astype(float), d[target].astype(int)
    model = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=5, eval_metric="logloss", random_state=SEED).fit(X, y)
    model.save_model(OUT / f"modelo_{name}.json")
    expl = shap.TreeExplainer(model)
    sv = expl.shap_values(X)  # log-odds
    S = pd.DataFrame(sv, columns=feats)

    glob = S.abs().mean().sort_values(ascending=False)
    fam = glob.groupby(lambda c: family(c)).sum().sort_values(ascending=False)
    result = {
        "modelo": name, "alvo": target, "n": int(len(d)), "positivos": float(y.mean()),
        "valor_base_logodds": float(np.ravel(expl.expected_value)[0]),
        "importancia": [{"variavel": c, "rotulo": LABELS.get(c, c), "familia": family(c), "media_abs_shap": round(float(v), 4)}
                        for c, v in glob.items()],
        "importancia_familia": {k: round(float(v), 4) for k, v in fam.items()},
        "participacao_nisar_pct": round(float(100 * fam.get("NISAR (radar 2026)", 0) / fam.sum()), 1),
    }
    (OUT / f"shap_{name}_global.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    pts = pd.concat([d[["id", "lon", "lat", group_col]], S.add_prefix("shap_")], axis=1)
    pts["prob"] = model.predict_proba(X)[:, 1]
    pts.to_csv(OUT / f"shap_{name}_pontos.csv", index=False)
    locais = {}
    for g, sub in pts.groupby(group_col):
        mean = sub[[f"shap_{c}" for c in feats]].mean()
        top = mean.reindex(mean.abs().sort_values(ascending=False).index)[:5]
        locais[str(g)] = {"pontos": int(len(sub)), "prob_media": round(float(sub.prob.mean()), 3),
                          "principais": [{"rotulo": LABELS.get(k[5:], k[5:]), "familia": family(k[5:]),
                                          "efeito": round(float(v), 3),
                                          "direcao": "aumenta risco" if v > 0 else "reduz risco"} for k, v in top.items()]}
    (OUT / f"shap_{name}_municipios.json").write_text(json.dumps(locais, ensure_ascii=False, indent=2), encoding="utf-8")

    shap.summary_plot(sv, X.rename(columns=LABELS), max_display=12, show=False, plot_size=(9, 6))
    plt.title(f"SHAP — {name}")
    plt.tight_layout()
    plt.savefig(OUT / f"shap_{name}_beeswarm.png", dpi=150)
    plt.close()
    print(name, "| NISAR responde por", result["participacao_nisar_pct"], "% da explicação |",
          ", ".join(f"{k}: {v:.3f}" for k, v in fam.items()))
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # 1) detector: histórico + clima + NISAR (alvo T2)
    d = pd.read_csv(DATA_PROCESSED / "final_5" / "modelo_previsao_pontos.csv")
    feats = [c for c in d.columns if c.startswith(("hist_", "clima_")) or
             (c.startswith("nisar_") and c not in ("nisar_n_dates", "nisar_rvi"))]
    explain("detector", d, feats, "T2_degradacao_uso")

    # 2) validador: só NISAR (degradado vs controle dos polígonos MODIS)
    v = pd.read_csv(DATA_PROCESSED / "tese_resultado" / "poligonos_pontos.csv")
    v["degradado"] = (v.classe == "degradado").astype(int)
    feats_v = [c for c in v.columns if c.startswith("nisar_") and c not in ("nisar_n_dates", "nisar_rvi")]
    explain("validador", v, feats_v, "degradado")

    # 3) suscetibilidade: contribuições aditivas por município
    s = pd.read_csv(DATA_PROCESSED / "final_5" / "suscetibilidade_5.csv", index_col=0)
    comps = [c for c in s.columns if c.startswith("comp_")]
    contrib = {m: {"indice_medio": float(r.indice_medio),
                   "contribuicoes": {c[5:]: round(float(r[c]) / len(comps), 3) for c in comps}}
               for m, r in s.iterrows()}
    (OUT / "contrib_suscetibilidade_municipios.json").write_text(json.dumps(contrib, ensure_ascii=False, indent=2), encoding="utf-8")
    print("suscetibilidade: contribuições salvas para", len(contrib), "municípios")


if __name__ == "__main__":
    main()
