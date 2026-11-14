"""Recorte de Pareto: municípios que somam 80% do prejuízo hidrológico.

Fonte: Atlas Digital de Desastres no Brasil (Sedec/MIDR), base consolidada
1991–2025 v1.1, aba "Atlas Valores Originais" (valores da época do registro).
Correção: IPCA (BCB SGS 433) até o último mês publicado.

Escolhas documentadas em `data/processed/atlas_summary.json`:
- Hidrológico = COBRADE 12100 inundação, 12200 enxurrada, 12300 alagamento.
  O grupo "Hidrológico" do Atlas também inclui movimento de massa e chuvas
  intensas; eles ficam de fora porque o NISAR mede água, não deslizamento.
- Prejuízo = danos materiais (DM_total_danos_materiais) + prejuízos econômicos
  públicos e privados (PE_PLePR).
- Valores monetários só a partir de 07/1994 (Plano Real). Antes disso, o
  evento conta como ocorrência, mas não entra na soma em R$.

Uso:
    python -m pipeline.atlas_pareto
"""

from __future__ import annotations

import json

import pandas as pd

from pipeline.config import DATA_PROCESSED, DATA_RAW

ATLAS_XLSX = DATA_RAW / "atlas" / "BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.xlsx"
ATLAS_SHEET = "Atlas Valores Originais"
IPCA_JSON = DATA_RAW / "bcb" / "ipca_433.json"
CACHE = DATA_PROCESSED / "atlas_original.parquet"

HYDRO_COBRADE = {12100: "Inundação", 12200: "Enxurrada", 12300: "Alagamento"}
REAL_START = pd.Timestamp("1994-07-01")
PARETO_SHARE = 0.80


def load_atlas() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    df = pd.read_excel(ATLAS_XLSX, sheet_name=ATLAS_SHEET)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.astype({c: str for c in df.columns if df[c].dtype == object}).to_parquet(CACHE)
    return df


def ipca_factors() -> tuple[pd.Series, pd.Period]:
    """Fator que leva R$ do mês m para R$ do último mês com IPCA publicado."""
    raw = pd.read_json(IPCA_JSON)
    raw["month"] = pd.to_datetime(raw["data"], dayfirst=True).dt.to_period("M")
    raw = raw.set_index("month")["valor"].astype(float).sort_index()
    # Índice no FIM de cada mês: preços do mês m valem index[m] / index[base].
    index = (1 + raw / 100).cumprod()
    base = index.index[-1]
    return index[base] / index, base


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-heavy-rain", action="store_true",
        help="Inclui COBRADE 13214 (chuvas intensas). As cheias do RS em 2024 foram registradas assim.",
    )
    args = parser.parse_args()
    hazards = dict(HYDRO_COBRADE)
    if args.with_heavy_rain:
        hazards[13214] = "Chuvas intensas"

    df = load_atlas()
    df["Cod_Cobrade"] = pd.to_numeric(df["Cod_Cobrade"], errors="coerce")
    hydro = df[df["Cod_Cobrade"].isin(hazards)].copy()
    hydro["event_date"] = pd.to_datetime(hydro["Data_Evento"], errors="coerce")

    money = ["DM_total_danos_materiais", "PE_PLePR", "PEPL_total_publico", "PEPR_total_privado"]
    for col in money:
        hydro[col] = pd.to_numeric(hydro[col], errors="coerce").fillna(0.0)

    factors, base = ipca_factors()
    month = hydro["event_date"].dt.to_period("M")
    hydro["ipca_factor"] = month.map(factors)
    valid_money = (hydro["event_date"] >= REAL_START) & hydro["ipca_factor"].notna()
    nominal = hydro["DM_total_danos_materiais"] + hydro["PE_PLePR"]
    hydro["loss_nominal_brl"] = nominal.where(valid_money, 0.0)
    hydro["loss_ipca_brl"] = (nominal * hydro["ipca_factor"]).where(valid_money, 0.0)

    by_mun = (
        hydro.groupby(["Cod_IBGE_Mun", "Nome_Municipio", "Sigla_UF", "regiao"], dropna=False)
        .agg(
            events=("Protocolo_S2iD", "count"),
            first_event=("event_date", "min"),
            last_event=("event_date", "max"),
            deaths=("DH_MORTOS", lambda s: pd.to_numeric(s, errors="coerce").sum()),
            displaced=("DH_DESALOJADOS", lambda s: pd.to_numeric(s, errors="coerce").sum()),
            homeless=("DH_DESABRIGADOS", lambda s: pd.to_numeric(s, errors="coerce").sum()),
            loss_nominal_brl=("loss_nominal_brl", "sum"),
            loss_ipca_brl=("loss_ipca_brl", "sum"),
        )
        .reset_index()
        .sort_values("loss_ipca_brl", ascending=False)
    )
    total = by_mun["loss_ipca_brl"].sum()
    by_mun["share"] = by_mun["loss_ipca_brl"] / total
    by_mun["cum_share"] = by_mun["share"].cumsum()
    # Inclui o município que cruza a linha dos 80%.
    by_mun["in_pareto"] = by_mun["cum_share"].shift(fill_value=0) < PARETO_SHARE

    by_type = hydro.groupby("Cod_Cobrade").agg(events=("Protocolo_S2iD", "count"), loss_ipca_brl=("loss_ipca_brl", "sum"))
    by_year = hydro.groupby(hydro["event_date"].dt.year)["loss_ipca_brl"].sum()
    pareto = by_mun[by_mun["in_pareto"]]

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    by_mun.to_csv(DATA_PROCESSED / "atlas_hidro_municipios.csv", index=False, encoding="utf-8")
    pareto.to_csv(DATA_PROCESSED / "atlas_recorte_pareto80.csv", index=False, encoding="utf-8")
    hydro.drop(columns=[c for c in hydro.columns if c.startswith(("DA_", "Setores"))]).to_parquet(
        DATA_PROCESSED / "atlas_hidro_eventos.parquet"
    )

    summary = {
        "source": "Atlas Digital de Desastres no Brasil — BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.xlsx",
        "source_url": "https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml",
        "sheet": ATLAS_SHEET,
        "hazards": hazards,
        "loss_definition": "DM_total_danos_materiais + PE_PLePR",
        "inflation": f"IPCA (BCB SGS 433), base {base}",
        "monetary_period_start": str(REAL_START.date()),
        "events": int(len(hydro)),
        "events_with_money": int(valid_money.sum()),
        "municipalities": int(len(by_mun)),
        "total_loss_ipca_brl": float(total),
        "pareto_share": PARETO_SHARE,
        "pareto_municipalities": int(len(pareto)),
        "pareto_loss_ipca_brl": float(pareto["loss_ipca_brl"].sum()),
        "by_type": {hazards[int(k)]: {"events": int(v.events), "loss_ipca_brl": float(v.loss_ipca_brl)} for k, v in by_type.iterrows()},
        "by_uf_in_pareto": pareto.groupby("Sigla_UF")["loss_ipca_brl"].sum().sort_values(ascending=False).round(0).to_dict(),
        "by_year": {int(k): float(v) for k, v in by_year.items() if pd.notna(k)},
        "limitations": [
            "Valores autodeclarados pelos municípios no FIDE/S2iD; subnotificação e erros de preenchimento.",
            "1991–1994 sem valores monetários comparáveis (antes do Real).",
            "Registros anteriores a 2013 foram digitalizados de protocolos em papel.",
            "Município com muitos registros pequenos pode ter perda real maior que a declarada.",
        ],
    }
    (DATA_PROCESSED / "atlas_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("events", "municipalities", "total_loss_ipca_brl", "pareto_municipalities", "by_type", "by_uf_in_pareto")}, ensure_ascii=False, indent=2))
    print(pareto.head(30)[["Nome_Municipio", "Sigla_UF", "events", "loss_ipca_brl", "cum_share"]].to_string(index=False))


if __name__ == "__main__":
    main()
